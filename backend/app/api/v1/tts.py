import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_

from app.db.session import get_db
from app.models.entities import User, Generation, Voice
from app.schemas.api import GenerationCreate, GenerationResponse, GenerationListResponse
from app.security.auth import get_current_user, get_current_user_or_default
from app.services.entitlement import entitlement_service
from app.workers.processor import generation_queue
from app.core.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Text to Speech"])

@router.post("/text-to-speech", response_model=GenerationResponse)
async def generate_speech(
    body: GenerationCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    # 1. Idempotency Check
    if idempotency_key:
        existing = await db.execute(
            select(Generation).where(
                Generation.user_id == current_user.id,
                Generation.idempotency_key == idempotency_key
            )
        )
        existing_gen = existing.scalar_one_or_none()
        if existing_gen:
            return existing_gen

    # 2. Strict Voice Validation & Routing
    # If client specified voice_type="cloned", route strictly to user's private custom clone
    if body.voice_type in ("cloned", "clone") or body.voice_id in ("user-clone", "your-clone"):
        v_res = await db.execute(
            select(Voice).where(
                or_(
                    Voice.id == body.voice_id,
                    Voice.slug == body.voice_id,
                    and_(
                        body.voice_id in ("user-clone", "your-clone"),
                        Voice.owner_user_id == current_user.id,
                        Voice.tier == "custom"
                    )
                ),
                Voice.is_active == True
            ).order_by(Voice.created_at.desc())
        )
        voice = v_res.scalars().first()
        if not voice:
            logger.error(f"[TTS Cloned Voice Routing] User clone '{body.voice_id}' not found or inactive for user '{current_user.id}'")
            raise AppException(
                status_code=404,
                error_code=ErrorCode.VOICE_NOT_FOUND,
                message=f"Selected cloned voice '{body.voice_id}' was not found. Never falling back to a library voice."
            )
    elif body.voice_type == "library":
        v_res = await db.execute(
            select(Voice).where(
                or_(Voice.id == body.voice_id, Voice.slug == body.voice_id),
                Voice.is_active == True
            )
        )
        voice = v_res.scalar_one_or_none()
        if not voice:
            logger.error(f"[TTS Library Voice Routing] Library voice '{body.voice_id}' not found")
            raise AppException(
                status_code=404,
                error_code=ErrorCode.VOICE_NOT_FOUND,
                message=f"Selected library voice '{body.voice_id}' was not found. Never auto-selecting another voice."
            )
    else:
        v_res = await db.execute(
            select(Voice).where(
                or_(Voice.id == body.voice_id, Voice.slug == body.voice_id),
                Voice.is_active == True
            )
        )
        voice = v_res.scalar_one_or_none()
        if not voice:
            logger.error(f"[TTS Voice Routing] Voice not found for voice_id='{body.voice_id}'")
            raise AppException(
                status_code=404,
                error_code=ErrorCode.VOICE_NOT_FOUND,
                message=f"Selected voice '{body.voice_id}' not found."
            )

    is_custom_clone = (voice.tier == "custom" or bool(voice.owner_user_id))
    if is_custom_clone and voice.owner_user_id and voice.owner_user_id != current_user.id and current_user.role != "admin":
        creator_result = await db.execute(select(User).where(User.email == "creator@hkspeaks.ai"))
        creator_user = creator_result.scalar_one_or_none()
        if not (creator_user and voice.owner_user_id == creator_user.id):
            raise AppException(
                status_code=403,
                error_code=ErrorCode.FORBIDDEN,
                message="You do not have access to this private cloned voice."
            )

    logger.info(
        f"[TTS Generation Request] user='{current_user.id}', request_voice_id='{body.voice_id}', "
        f"request_voice_type='{body.voice_type}', matched_voice_id='{voice.id}', "
        f"matched_voice_name='{voice.name}', tier='{voice.tier}', type='{voice.type}', "
        f"provider='{voice.provider}', model='{voice.model}', "
        f"provider_voice_id='{voice.provider_voice_id}'"
    )

    # 3. Entitlement & Quota Check
    text_len = len(body.text.strip())
    if text_len == 0:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.INVALID_TEXT,
            message="Input text cannot be empty."
        )

    await entitlement_service.check_can_generate(db, current_user, voice, text_len)

    # 4. Create Generation record (queued)
    estimated_duration = round(max(1.0, text_len / 15.0), 2)
    settings_data = {
        "speed": body.speed or 1.0,
        "pitch": body.pitch or 0.0,
        "stability": body.stability or 0.5,
        "similarity": body.similarity or 0.75,
        "style": body.style or 0.0,
        "is_clone": is_custom_clone,
        "cloned_voice_id": voice.id if is_custom_clone else None,
        "voice_tier": voice.tier,
    }

    generation = Generation(
        user_id=current_user.id,
        project_document_id=body.project_document_id,
        voice_id=voice.id,
        provider=voice.provider,
        model=voice.model,
        input_text=body.text,
        input_characters=text_len,
        estimated_audio_seconds=estimated_duration,
        format=body.format,
        status="queued",
        idempotency_key=idempotency_key,
        settings_json=settings_data
    )
    db.add(generation)
    await db.flush()

    # 5. Reserve Credits in Ledger
    await entitlement_service.reserve_credit(db, current_user.id, generation.id, text_len)
    await db.commit()
    await db.refresh(generation)

    # 6. Enqueue Background Processing (Non-blocking!)
    await generation_queue.enqueue(generation.id)

    # Populate voice name in response
    resp = GenerationResponse.model_validate(generation)
    resp.voice_name = voice.name
    return resp

@router.get("/generations/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    gen = result.scalar_one_or_none()
    if not gen:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Generation not found."
        )

    # Ownership check
    if gen.user_id != current_user.id and current_user.role != "admin":
        raise AppException(
            status_code=403,
            error_code=ErrorCode.FORBIDDEN,
            message="You do not have access to this generation."
        )

    v_res = await db.execute(select(Voice).where(Voice.id == gen.voice_id))
    voice = v_res.scalar_one_or_none()

    resp = GenerationResponse.model_validate(gen)
    if voice:
        resp.voice_name = voice.name
    return resp

@router.get("/generations", response_model=GenerationListResponse)
async def list_generations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    base_filter = [Generation.user_id == current_user.id]
    if status:
        base_filter.append(Generation.status == status)

    # Total count
    total_res = await db.execute(select(func.count(Generation.id)).where(*base_filter))
    total = total_res.scalar_one()

    # Paginate with joined voice
    query = (
        select(Generation)
        .where(*base_filter)
        .options(joinedload(Generation.voice))
        .order_by(desc(Generation.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    generations = result.scalars().all()

    items = []
    for g in generations:
        r = GenerationResponse.model_validate(g)
        if g.voice:
            r.voice_name = g.voice.name
        items.append(r)

    return GenerationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.delete("/generations")
async def clear_all_generations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.storage import storage_service
    res = await db.execute(select(Generation).where(Generation.user_id == current_user.id))
    gens = res.scalars().all()
    count = 0
    for g in gens:
        if g.storage_key:
            try:
                await storage_service.delete_audio(g.storage_key)
            except Exception:
                pass
        await db.delete(g)
        count += 1
    await db.commit()
    return {"message": f"Successfully cleared {count} generations.", "deleted_count": count}

@router.delete("/generations/{generation_id}")
async def delete_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.storage import storage_service
    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    gen = result.scalar_one_or_none()
    if not gen:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Generation not found.")

    if gen.user_id != current_user.id and current_user.role != "admin":
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    # Delete storage file if exists
    if gen.storage_key:
        try:
            await storage_service.delete_audio(gen.storage_key)
        except Exception:
            pass

    await db.delete(gen)
    await db.commit()
    return {"message": "Generation deleted successfully."}

@router.post("/generations/{generation_id}/cancel")
async def cancel_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    gen = result.scalar_one_or_none()
    if not gen:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Generation not found.")

    if gen.user_id != current_user.id:
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Permission denied.")

    if gen.status in ["completed", "failed", "cancelled"]:
        return {"status": gen.status, "message": f"Generation is already {gen.status}."}

    gen.status = "cancelled"
    await db.commit()

    # Refund reserved credits
    await entitlement_service.refund_reservation(
        db, gen.user_id, gen.id, gen.input_characters, reason="User cancelled generation"
    )

    return {"status": "cancelled", "message": "Generation successfully cancelled."}
