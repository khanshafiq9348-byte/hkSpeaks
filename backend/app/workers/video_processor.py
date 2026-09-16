import os
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import async_session_maker
from app.models.video_entities import (
    VideoProject, VideoAsset, Voiceover, TranscriptSegment,
    Scene, ImageAnalysis, TimelineClip, TimelineTransition, TimelineEffect,
    RenderJob, RenderOutput
)
from app.video.engine import documentary_engine
from app.video.renderer import ffmpeg_renderer
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

async def run_render_job(render_job_id: str):
    """
    Executes a video rendering job asynchronously with real-time step and progress updates.
    """
    async with async_session_maker() as db:
        res = await db.execute(
            select(RenderJob).where(RenderJob.id == render_job_id)
        )
        job = res.scalar_one_or_none()
        if not job:
            logger.error(f"Render job {render_job_id} not found.")
            return

        try:
            job.status = "rendering"
            job.started_at = datetime.now(timezone.utc)
            job.progress = 5.0
            job.current_step = "Preparing project assets..."
            await db.commit()

            # Load project with voiceover and timeline clips
            proj_res = await db.execute(
                select(VideoProject)
                .where(VideoProject.id == job.project_id)
                .options(
                    selectinload(VideoProject.voiceover),
                    selectinload(VideoProject.timeline_clips).selectinload(TimelineClip.asset),
                    selectinload(VideoProject.timeline_clips).selectinload(TimelineClip.effects)
                )
            )
            project = proj_res.scalar_one_or_none()
            if not project:
                raise ValueError("Project not found.")
            if not project.voiceover:
                raise ValueError("Project has no master voiceover audio.")
            if not project.timeline_clips:
                raise ValueError("Project has no timeline clips.")

            vo_path = storage_service.get_local_path(project.voiceover.storage_key)
            if not vo_path or not os.path.exists(vo_path):
                raise FileNotFoundError(f"Voiceover file missing on disk: {project.voiceover.storage_key}")

            job.progress = 20.0
            job.current_step = "Compiling timeline clips..."
            await db.commit()

            # Assemble clips data for renderer
            clips_data = []
            for c in project.timeline_clips:
                img_path = storage_service.get_local_path(c.asset.storage_key)
                if not img_path or not os.path.exists(img_path):
                    raise FileNotFoundError(f"Asset image missing on disk: {c.asset.filename}")
                effect_type = "cinematic_grade"
                if c.effects:
                    effect_type = c.effects[0].effect_type

                clips_data.append({
                    "image_path": img_path,
                    "duration": c.duration,
                    "motion_type": c.motion_type,
                    "effect_type": effect_type
                })

            job.progress = 35.0
            job.current_step = "Starting FFmpeg render..."
            await db.commit()

            # Output filename
            render_filename = f"documentary_{project.id[:8]}_{job.id[:8]}.mp4"
            render_storage_key = f"users/{project.user_id}/video_projects/{project.id}/renders/{render_filename}"
            render_local_path = os.path.join(storage_service.local_dir, render_storage_key.replace("/", os.sep))

            loop = asyncio.get_running_loop()
            last_progress_time = 0.0
            last_progress_pct = 0.0

            def on_progress(pct: float, step: str):
                nonlocal last_progress_time, last_progress_pct
                import time
                now = time.time()
                if pct < 99.0 and (pct - last_progress_pct < 1.0) and (now - last_progress_time < 1.0):
                    return
                last_progress_time = now
                last_progress_pct = pct

                async def _update_db():
                    try:
                        async with async_session_maker() as update_db:
                            res_u = await update_db.execute(select(RenderJob).where(RenderJob.id == render_job_id))
                            job_u = res_u.scalar_one_or_none()
                            if job_u and job_u.status == "rendering":
                                job_u.progress = round(pct, 1)
                                job_u.current_step = step
                                await update_db.commit()
                    except Exception as err:
                        logger.debug(f"Progress DB update error: {err}")

                try:
                    asyncio.run_coroutine_threadsafe(_update_db(), loop)
                except Exception:
                    pass

            render_result = await asyncio.to_thread(
                ffmpeg_renderer.render_documentary,
                clips_data=clips_data,
                voiceover_audio_path=vo_path,
                output_file_path=render_local_path,
                aspect_ratio=job.aspect_ratio,
                resolution=job.resolution,
                fps=job.fps,
                progress_callback=on_progress
            )

            job.progress = 95.0
            job.current_step = "Saving rendered documentary..."
            await db.commit()

            download_url = f"{storage_service.provider_url if hasattr(storage_service, 'provider_url') else '/v1/storage'}/{render_storage_key}"
            if download_url.startswith("/v1/storage"):
                download_url = f"http://localhost:8000{download_url}"

            # Create RenderOutput
            output = RenderOutput(
                project_id=project.id,
                render_job_id=job.id,
                filename=render_filename,
                storage_key=render_storage_key,
                download_url=download_url,
                duration=project.total_duration,
                file_size=render_result["file_size"],
                format="mp4",
                codec="h264",
                resolution=render_result["resolution"]
            )
            db.add(output)

            job.status = "completed"
            job.progress = 100.0
            job.current_step = "Completed"
            job.completed_at = datetime.now(timezone.utc)
            project.status = "completed"

            await db.commit()
            logger.info(f"Render job {job.id} completed successfully: {render_filename} ({render_result['file_size']} bytes)")

        except Exception as e:
            logger.error(f"Render job {render_job_id} failed: {e}", exc_info=True)
            try:
                res = await db.execute(select(RenderJob).where(RenderJob.id == render_job_id))
                failed_job = res.scalar_one_or_none()
                if failed_job:
                    failed_job.status = "failed"
                    failed_job.error_message = str(e)[:400]
                    failed_job.current_step = "Failed"
                    await db.commit()
            except Exception as ex2:
                logger.error(f"Failed to record render job error: {ex2}")

class VideoRenderQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task = None

    async def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            asyncio.create_task(self._recover_interrupted_jobs())

    async def _recover_interrupted_jobs(self):
        await asyncio.sleep(2.0)
        try:
            async with async_session_maker() as db:
                res = await db.execute(
                    select(RenderJob).where(RenderJob.status.in_(["rendering", "queued"]))
                )
                interrupted = res.scalars().all()
                for j in interrupted:
                    logger.info(f"Auto-resuming interrupted render job {j.id}...")
                    await self._queue.put(j.id)
        except Exception as e:
            logger.error(f"Failed to recover interrupted render jobs: {e}")

    async def enqueue(self, render_job_id: str):
        await self._queue.put(render_job_id)
        await self.start()

    async def _worker_loop(self):
        while True:
            try:
                render_job_id = await self._queue.get()
                await run_render_job(render_job_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in video render worker queue: {e}")
                await asyncio.sleep(1.0)

video_render_queue = VideoRenderQueue()
