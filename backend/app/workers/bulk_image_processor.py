import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.bulk_image_entities import BulkImageBatch, BulkImageItem
from app.services.image_generator import image_generator_service

logger = logging.getLogger(__name__)

# Provider-aware controlled parallel workers (concurrency of 2 with automatic 429 exponential backoff)
_worker_sem = asyncio.Semaphore(2)

async def process_bulk_batch_job(batch_id: str):
    async with async_session_maker() as db:
        res = await db.execute(select(BulkImageBatch).where(BulkImageBatch.id == batch_id))
        batch = res.scalar_one_or_none()
        if not batch:
            logger.error(f"BulkImageBatch {batch_id} not found.")
            return

        batch.status = "processing"
        await db.commit()

        # Load all items in batch
        items_res = await db.execute(
            select(BulkImageItem)
            .where(BulkImageItem.batch_id == batch_id)
            .order_by(BulkImageItem.prompt_index)
        )
        items = items_res.scalars().all()

        completed_count = 0
        failed_count = 0
        total = len(items)

        # Calculate native generation dimensions based on batch settings
        res_mult = {
            "720p": 1.0,
            "1080p": 1.5,
            "2K": 2.0
        }.get(batch.resolution, 1.5)

        if batch.aspect_ratio == "1:1":
            base_w, base_h = int(768 * res_mult), int(768 * res_mult)
        elif batch.aspect_ratio == "9:16":
            base_w, base_h = int(576 * res_mult), int(1024 * res_mult)
        else: # 16:9
            base_w, base_h = int(1024 * res_mult), int(576 * res_mult)

        w, h = min(2048, base_w), min(2048, base_h)
        db_lock = asyncio.Lock()

        async def generate_item(item: BulkImageItem, delay_start: float = 0.0):
            nonlocal completed_count, failed_count
            if item.status == "completed" and item.image_url:
                completed_count += 1
                return

            if delay_start > 0:
                await asyncio.sleep(delay_start)

            # Controlled worker concurrency
            async with _worker_sem:
                # Mark item generating in DB so UI displays "Rendering..." immediately
                async with db_lock:
                    async with async_session_maker() as item_db:
                        i_res = await item_db.execute(select(BulkImageItem).where(BulkImageItem.id == item.id))
                        db_it = i_res.scalar_one_or_none()
                        if db_it:
                            db_it.status = "generating"
                            await item_db.commit()

                try:
                    s_key, url = await image_generator_service.generate_single_image(
                        prompt=item.prompt_text,
                        user_id=batch.user_id,
                        batch_id=batch.id,
                        item_id=item.id,
                        index=item.prompt_index,
                        width=w,
                        height=h,
                        seed=item.seed
                    )
                    item.storage_key = s_key
                    item.image_url = url
                    item.status = "completed"
                    item.error_message = None
                    item.completed_at = datetime.now(timezone.utc)
                    completed_count += 1

                    # Commit item and batch progress safely under db_lock
                    async with db_lock:
                        async with async_session_maker() as item_db:
                            i_res = await item_db.execute(select(BulkImageItem).where(BulkImageItem.id == item.id))
                            db_it = i_res.scalar_one_or_none()
                            if db_it:
                                db_it.storage_key = s_key
                                db_it.image_url = url
                                db_it.status = "completed"
                                db_it.error_message = None
                                db_it.completed_at = datetime.now(timezone.utc)

                            b_res = await item_db.execute(select(BulkImageBatch).where(BulkImageBatch.id == batch_id))
                            b_obj = b_res.scalar_one_or_none()
                            if b_obj:
                                b_obj.completed_count = completed_count
                                b_obj.failed_count = failed_count
                                b_obj.progress_pct = round(((completed_count + failed_count) / max(1, total)) * 100, 1)
                            await item_db.commit()
                except Exception as e:
                    # One failed item NEVER stops or blocks the remaining items in the batch
                    logger.error(f"Item #{item.prompt_index} ({item.id}) failed: {e}")
                    item.status = "failed"
                    item.error_message = str(e)[:250]
                    failed_count += 1

                    async with db_lock:
                        async with async_session_maker() as item_db:
                            i_res = await item_db.execute(select(BulkImageItem).where(BulkImageItem.id == item.id))
                            db_it = i_res.scalar_one_or_none()
                            if db_it:
                                db_it.status = "failed"
                                db_it.error_message = str(e)[:250]

                            b_res = await item_db.execute(select(BulkImageBatch).where(BulkImageBatch.id == batch_id))
                            b_obj = b_res.scalar_one_or_none()
                            if b_obj:
                                b_obj.completed_count = completed_count
                                b_obj.failed_count = failed_count
                                b_obj.progress_pct = round(((completed_count + failed_count) / max(1, total)) * 100, 1)
                            await item_db.commit()
                finally:
                    # Brief pacing cooldown between jobs
                    await asyncio.sleep(0.6)

        # Execute generation in controlled parallel tasks with staggered start
        tasks = [generate_item(it, delay_start=min(5.0, idx * 0.75)) for idx, it in enumerate(items)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Build ZIP file containing all completed images
        zip_key, zip_url, zip_size = image_generator_service.create_batch_zip(
            batch_id=batch.id,
            user_id=batch.user_id,
            items=items
        )

        async with async_session_maker() as final_db:
            f_res = await final_db.execute(select(BulkImageBatch).where(BulkImageBatch.id == batch_id))
            final_batch = f_res.scalar_one_or_none()
            if final_batch:
                final_batch.completed_count = completed_count
                final_batch.failed_count = failed_count
                final_batch.progress_pct = 100.0
                final_batch.zip_url = zip_url
                final_batch.zip_storage_key = zip_key
                final_batch.zip_size_bytes = zip_size
                final_batch.status = "completed" if failed_count == 0 else ("partial" if completed_count > 0 else "failed")
                final_batch.completed_at = datetime.now(timezone.utc)
                final_batch.updated_at = datetime.now(timezone.utc)
                await final_db.commit()
        logger.info(f"BulkImageBatch {batch_id} completed. {completed_count}/{total} images generated. ZIP ready at {zip_url}")

class BulkImageQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task = None

    async def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def enqueue(self, batch_id: str):
        await self._queue.put(batch_id)
        await self.start()

    async def _worker_loop(self):
        while True:
            try:
                batch_id = await self._queue.get()
                await process_bulk_batch_job(batch_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in bulk image worker queue: {e}")
                await asyncio.sleep(1.0)

bulk_image_queue = BulkImageQueue()
