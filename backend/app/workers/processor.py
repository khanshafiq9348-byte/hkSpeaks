import re
import asyncio
import logging
from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.entities import Generation, Voice, UsageRecord
from app.providers.router import tts_router
from app.providers.base import TTSRequest
from app.audio.processor import audio_processor
from app.services.storage import storage_service
from app.services.entitlement import entitlement_service
from app.core.config import settings

logger = logging.getLogger(__name__)

def split_text_into_chunks(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Splits long scripts into clean chunks respecting sentence boundaries and paragraphs.
    """
    text = text.strip()
    if len(text) <= max_chunk_size:
        return [text]

    # Split by paragraphs first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue

        if len(current_chunk) + len(p) + 2 <= max_chunk_size:
            current_chunk = f"{current_chunk}\n\n{p}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # If a single paragraph exceeds max_chunk_size, split by sentences
            if len(p) > max_chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', p)
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(current_chunk) + len(s) + 1 <= max_chunk_size:
                        current_chunk = f"{current_chunk} {s}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = s
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]

async def process_generation_job(generation_id: str):
    """
    Executes a single TTS generation background job asynchronously.
    """
    async with async_session_maker() as db:
        try:
            # 1. Fetch generation
            result = await db.execute(select(Generation).where(Generation.id == generation_id))
            gen = result.scalar_one_or_none()
            if not gen or gen.status == "cancelled":
                return

            # Mark processing
            gen.status = "processing"
            await db.commit()

            # 2. Fetch voice
            v_res = await db.execute(select(Voice).where(Voice.id == gen.voice_id))
            voice = v_res.scalar_one_or_none()
            if not voice:
                logger.error(f"[TTS Trace Worker] Referenced voice '{gen.voice_id}' not found for generation '{gen.id}'")
                raise ValueError(f"Referenced voice '{gen.voice_id}' no longer exists.")

            logger.info(f"[TTS Trace Worker] Processing generation '{gen.id}' with voice '{voice.name}' (id='{voice.id}', tier='{voice.tier}', model='{voice.model}', provider='{voice.provider}')")

            # 3. Text chunking
            chunks = split_text_into_chunks(gen.input_text, settings.DEFAULT_CHUNK_SIZE_CHARS)
            chunk_audio_bytes = []
            total_estimated_cost = 0.0

            settings_data = gen.settings_json or {}
            speed = float(settings_data.get("speed", 1.0))
            pitch = float(settings_data.get("pitch", 0.0))
            style = float(settings_data.get("style", 0.0))
            stability = float(settings_data.get("stability", 0.5))
            similarity = float(settings_data.get("similarity", 0.75))
            is_cloned_voice = bool(voice.tier == "custom" or voice.owner_user_id)

            for chunk_text in chunks:
                req = TTSRequest(
                    text=chunk_text,
                    voice_id=voice.id,
                    provider_voice_id=voice.provider_voice_id,
                    language=voice.language,
                    locale=voice.locale,
                    gender=voice.gender,
                    model=gen.model or voice.model,
                    speed=speed,
                    pitch=pitch,
                    style=style,
                    stability=stability,
                    similarity=similarity,
                    format=gen.format,
                    tier=voice.tier,
                    is_clone=is_cloned_voice
                )
                
                # Estimate cost
                cost = tts_router.estimate_cost(req, voice.provider)
                total_estimated_cost += cost.estimated_amount

                # Synthesize chunk
                tts_result = await tts_router.synthesize(req, preferred_provider=voice.provider)
                chunk_audio_bytes.append(tts_result.audio_bytes)
                if not gen.provider_request_id:
                    gen.provider_request_id = tts_result.provider_request_id

            # 4. Concatenate and normalize chunks if multiple
            if len(chunk_audio_bytes) > 1:
                final_audio = await audio_processor.concatenate_audio_chunks(chunk_audio_bytes, gen.format)
            else:
                final_audio = chunk_audio_bytes[0]

            # 5. Validate audio & get actual duration
            actual_duration, _ = await audio_processor.get_audio_duration_and_validate(final_audio)

            # 6. Upload to storage
            file_ext = gen.format.lower()
            storage_key = f"users/{gen.user_id}/generations/{gen.id}/output.{file_ext}"
            content_type = "audio/mpeg" if file_ext == "mp3" else "audio/wav"
            audio_url = await storage_service.upload_audio(storage_key, final_audio, content_type)

            # 7. Update generation state to completed
            gen.status = "completed"
            gen.actual_audio_seconds = actual_duration
            gen.storage_key = storage_key
            gen.audio_url = audio_url
            gen.estimated_cost = round(total_estimated_cost, 6)
            gen.completed_at = datetime.now(timezone.utc)

            # 8. Record usage record
            usage_rec = UsageRecord(
                user_id=gen.user_id,
                generation_id=gen.id,
                usage_type="tts_generation",
                units=gen.input_characters,
                unit_type="characters",
                model=gen.model,
                provider=voice.provider,
                estimated_cost=gen.estimated_cost
            )
            db.add(usage_rec)

            # 9. Finalize credit ledger
            await entitlement_service.finalize_usage(db, gen.user_id, gen.id, gen.input_characters)
            await db.commit()
            logger.info(f"Generation {gen.id} completed successfully ({actual_duration}s).")

        except Exception as e:
            logger.error(f"Generation {generation_id} failed: {e}")
            try:
                # Reload generation to update error
                res = await db.execute(select(Generation).where(Generation.id == generation_id))
                gen = res.scalar_one_or_none()
                if gen:
                    err_code = getattr(e, "error_code", None) or "GENERATION_FAILED"
                    if hasattr(err_code, "value"):
                        err_code = err_code.value
                    err_msg = getattr(e, "message", None) or str(e)

                    gen.status = "failed"
                    gen.error_code = err_code
                    gen.error_message = str(err_msg)[:300]
                    await db.commit()

                    # Refund credit reservation
                    await entitlement_service.refund_reservation(
                        db, gen.user_id, gen.id, gen.input_characters, reason=str(err_msg)[:100]
                    )
            except Exception as rollback_err:
                logger.error(f"Failed to record generation failure: {rollback_err}")

# In-memory queue worker for immediate asynchronous background execution
class GenerationQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task = None

    async def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def enqueue(self, generation_id: str):
        await self._queue.put(generation_id)
        # Ensure worker is running
        await self.start()

    async def _worker_loop(self):
        while True:
            try:
                generation_id = await self._queue.get()
                await process_generation_job(generation_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in generation worker queue: {e}")
                await asyncio.sleep(1.0)

generation_queue = GenerationQueue()
