import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.prompt_entities import AudioPromptProject, PromptScene
from app.services.prompt_engine import PromptEngine

logger = logging.getLogger(__name__)

async def process_prompt_project_job(project_id: str):
    async with async_session_maker() as db:
        try:
            res = await db.execute(select(AudioPromptProject).where(AudioPromptProject.id == project_id))
            proj = res.scalar_one_or_none()
            if not proj:
                logger.error(f"AudioPromptProject {project_id} not found.")
                return

            proj.status = "processing"
            await db.commit()

            # Analyze audio & generate scene prompts
            scenes_data = PromptEngine.analyze_audio_and_generate_scenes(
                audio_path=proj.audio_storage_key,
                total_duration=proj.total_duration,
                style_preset=proj.style_preset
            )

            # Clear old scenes if any
            old_scenes_res = await db.execute(select(PromptScene).where(PromptScene.project_id == project_id))
            for old_s in old_scenes_res.scalars().all():
                await db.delete(old_s)

            for sdata in scenes_data:
                scene = PromptScene(
                    project_id=project_id,
                    scene_index=sdata["scene_index"],
                    start_time=sdata["start_time"],
                    end_time=sdata["end_time"],
                    duration=sdata["duration"],
                    transcript_text=sdata["transcript_text"],
                    image_prompt=sdata["image_prompt"],
                    negative_prompt=sdata["negative_prompt"],
                    aspect_ratio=sdata["aspect_ratio"]
                )
                db.add(scene)

            proj.total_scenes = len(scenes_data)
            proj.status = "completed"
            proj.error_message = None
            proj.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"AudioPromptProject {project_id} completed with {len(scenes_data)} scene prompts.")

        except Exception as e:
            logger.error(f"AudioPromptProject {project_id} failed: {e}")
            try:
                res = await db.execute(select(AudioPromptProject).where(AudioPromptProject.id == project_id))
                proj = res.scalar_one_or_none()
                if proj:
                    proj.status = "failed"
                    proj.error_message = str(e)[:300]
                    await db.commit()
            except Exception:
                pass

class PromptQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task = None

    async def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def enqueue(self, project_id: str):
        await self._queue.put(project_id)
        await self.start()

    async def _worker_loop(self):
        while True:
            try:
                project_id = await self._queue.get()
                await process_prompt_project_job(project_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in prompt queue worker: {e}")
                await asyncio.sleep(1.0)

prompt_queue = PromptQueue()
