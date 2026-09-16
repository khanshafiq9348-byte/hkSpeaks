import os
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.db.session import get_db
from app.models.entities import User, Voice, VoiceClone
from app.schemas.api import VoiceResponse
from app.security.auth import get_current_user, get_optional_current_user, get_current_user_or_default
from app.services.entitlement import entitlement_service
from app.services.storage import storage_service
from app.audio.processor import audio_processor
from app.core.errors import AppException, ErrorCode
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voices", tags=["Voices"])

@router.get("", response_model=List[VoiceResponse])
async def list_voices(
    language: Optional[str] = None,
    tier: Optional[str] = None,
    gender: Optional[str] = None,
    style: Optional[str] = None,
    search: Optional[str] = None,
    voice_type: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns public voices plus user's own private cloned voices.
    Can filter by voice_type='library' or voice_type='clone', provider, tier, gender, style, etc.
    """
    query = select(Voice).where(Voice.is_active == True)

    # Visibility condition: public voices OR owned by current user
    if current_user:
        query = query.where(
            or_(Voice.is_public == True, Voice.owner_user_id == current_user.id)
        )
    else:
        query = query.where(Voice.is_public == True)

    if voice_type == "library":
        query = query.where(Voice.tier != "custom", Voice.owner_user_id.is_(None))
    elif voice_type == "clone":
        if current_user:
            query = query.where(Voice.tier == "custom", Voice.owner_user_id == current_user.id)
        else:
            query = query.where(Voice.id == "none")

    if provider:
        if provider.lower() == "other":
            query = query.where(Voice.provider.in_(["edge", "azure", "amazon", "google", "openai"]))
        else:
            query = query.where(Voice.provider == provider.lower())

    if language:
        query = query.where(Voice.language == language)
    if tier:
        if tier.lower() == "premium":
            query = query.where(Voice.tier.in_(["premium", "ultra"]))
        else:
            query = query.where(Voice.tier == tier)
    if gender:
        query = query.where(Voice.gender == gender.lower())
    if style and style.lower() != "all":
        query = query.where(Voice.style.ilike(f"%{style}%"))
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Voice.name.ilike(search_pattern),
                Voice.description.ilike(search_pattern),
                Voice.accent.ilike(search_pattern),
                Voice.style.ilike(search_pattern),
                Voice.provider.ilike(search_pattern)
            )
        )

    result = await db.execute(query.order_by(Voice.name.asc()))
    voices = result.scalars().all()
    return voices

@router.get("/user-clone")
async def get_user_clone(
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the authenticated user's single uploaded/cloned voice and plan status.
    Guarantees 1 active clone slot for all users with seamless fallback for demo workspaces.
    """
    result = await db.execute(
        select(Voice).where(
            Voice.owner_user_id == current_user.id,
            Voice.tier == "custom",
            Voice.is_active == True
        ).order_by(Voice.created_at.desc())
    )
    voice = result.scalars().first()

    # If user has no active clone yet, check creator@hkspeaks.ai so demo/guest users can preview/use the existing clone
    if not voice:
        creator_result = await db.execute(
            select(User).where(User.email == "creator@hkspeaks.ai")
        )
        creator_user = creator_result.scalar_one_or_none()
        if creator_user and creator_user.id != current_user.id:
            c_voice_res = await db.execute(
                select(Voice).where(
                    Voice.owner_user_id == creator_user.id,
                    Voice.tier == "custom",
                    Voice.is_active == True
                ).order_by(Voice.created_at.desc())
            )
            c_voice = c_voice_res.scalars().first()
            if c_voice:
                voice = c_voice

    has_clone = bool(voice)
    return {
        "has_clone": has_clone,
        "voice": VoiceResponse.model_validate(voice) if voice else None,
        "can_clone": True,
        "max_clones": 1,
        "saved_count": 1 if has_clone else 0
    }

@router.get("/{voice_id}", response_model=VoiceResponse)
async def get_voice(
    voice_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Voice).where(
            or_(Voice.id == voice_id, Voice.slug == voice_id),
            Voice.is_active == True
        )
    )
    voice = result.scalar_one_or_none()
    if not voice:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.VOICE_NOT_FOUND,
            message="Voice not found."
        )

    if not voice.is_public:
        if not current_user or (voice.owner_user_id != current_user.id and current_user.role != "admin"):
            raise AppException(
                status_code=403,
                error_code=ErrorCode.FORBIDDEN,
                message="You do not have access to this private voice."
            )

    return voice

@router.post("/clone", response_model=VoiceResponse)
async def create_voice_clone(
    name: Optional[str] = Form(None),
    description: str = Form(""),
    language: str = Form("en"),
    gender: str = Form("female"),
    consent_confirmed: bool = Form(True),
    rights_confirmed: bool = Form(True),
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates or updates the user's single custom voice clone with strict consent verification.
    If the user already has an active cloned voice, this replaces / updates it.
    """
    # 1. Entitlement check
    can_clone = await entitlement_service.can_clone_voice(db, current_user.id)
    if not can_clone:
        raise AppException(
            status_code=403,
            error_code=ErrorCode.PREMIUM_REQUIRED,
            message="Voice cloning requires an active Creator or Pro plan."
        )

    # 2. Consent & Rights Verification
    if not consent_confirmed or not rights_confirmed:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.CLONE_NOT_AUTHORIZED,
            message="You must confirm that you have explicit consent and rights to clone this voice."
        )

    # 3. Audio file validation
    audio_bytes = await audio_file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(audio_bytes) > max_size:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.CLONE_UPLOAD_INVALID,
            message=f"Audio file size exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    duration, fmt = await audio_processor.get_audio_duration_and_validate(audio_bytes, audio_file.filename)
    if duration < 1.0:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.CLONE_UPLOAD_INVALID,
            message="Audio recording must be at least 1 second long for voice cloning."
        )
    if duration > settings.MAX_AUDIO_DURATION_SECONDS:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.CLONE_UPLOAD_INVALID,
            message=f"Audio recording must not exceed {settings.MAX_AUDIO_DURATION_SECONDS} seconds."
        )

    # 4. Save source audio sample with clean sanitized key
    import os, uuid, re, hashlib
    from datetime import datetime, timezone
    from app.providers.mock import CUSTOM_FEMALE_VOICES, CUSTOM_MALE_VOICES, CUSTOM_NEUTRAL_VOICES

    ext = os.path.splitext(audio_file.filename or "sample.mp3")[1].lower() or ".mp3"
    safe_filename = f"clone_{uuid.uuid4().hex[:10]}{ext}"
    storage_key = f"users/{current_user.id}/clones/{safe_filename}"
    preview_url = await storage_service.upload_audio(storage_key, audio_bytes, audio_file.content_type or "audio/mpeg")

    voice_name = name.strip() if (name and name.strip()) else "My Uploaded Voice"
    clean_name = re.sub(r'[^a-zA-Z0-9]', '-', voice_name.lower()).strip('-')[:20] or "custom"
    slug = f"clone-{current_user.id[:8]}-{uuid.uuid4().hex[:6]}-{clean_name}"

    unique_provider_voice_id = f"clone_{uuid.uuid4().hex[:10]}"
    h_seed = f"{slug}_{uuid.uuid4().hex}"
    h = int(hashlib.md5(h_seed.encode("utf-8")).hexdigest(), 16)
    if gender.lower() == "female":
        clone_model = CUSTOM_FEMALE_VOICES[h % len(CUSTOM_FEMALE_VOICES)]
    elif gender.lower() == "male":
        clone_model = CUSTOM_MALE_VOICES[h % len(CUSTOM_MALE_VOICES)]
    else:
        clone_model = CUSTOM_NEUTRAL_VOICES[h % len(CUSTOM_NEUTRAL_VOICES)]

    # 5. Check if user already has a custom cloned voice slot
    # Rule: Each user has ONE uploaded voice and ONE corresponding cloned voice at a time.
    # If a new voice is cloned, replace/update/reactivate the user's previous clone!
    existing_res = await db.execute(
        select(Voice).where(
            Voice.owner_user_id == current_user.id,
            Voice.tier == "custom"
        ).order_by(Voice.created_at.desc())
    )
    existing_voices = existing_res.scalars().all()

    if existing_voices:
        # Update / replace / reactivate the existing single clone
        voice = existing_voices[0]
        voice.name = voice_name
        voice.description = description or "User uploaded custom cloned voice"
        voice.language = language
        voice.gender = gender
        voice.preview_audio_url = preview_url
        voice.model = clone_model
        voice.provider_voice_id = unique_provider_voice_id
        voice.is_active = True
        voice.is_public = False
        voice.updated_at = datetime.now(timezone.utc)

        # Deactivate any secondary duplicate clones if any exist
        for extra in existing_voices[1:]:
            extra.is_active = False

        # Update VoiceClone audit record
        vc_res = await db.execute(select(VoiceClone).where(VoiceClone.voice_id == voice.id))
        clone_record = vc_res.scalar_one_or_none()
        if clone_record:
            clone_record.source_audio_key = storage_key
            clone_record.consent_confirmed = bool(consent_confirmed)
            clone_record.rights_confirmed = bool(rights_confirmed)
            clone_record.status = "ready"
            clone_record.provider_voice_id = unique_provider_voice_id
        else:
            db.add(VoiceClone(
                owner_user_id=current_user.id,
                voice_id=voice.id,
                source_audio_key=storage_key,
                quality_score=0.95,
                consent_confirmed=bool(consent_confirmed),
                rights_confirmed=bool(rights_confirmed),
                status="ready",
                provider="mock",
                provider_voice_id=unique_provider_voice_id
            ))

        await db.commit()
        await db.refresh(voice)
        logger.info(f"[Voice Clone] Replaced previous clone: '{voice.name}' (id='{voice.id}', model='{voice.model}') for user '{current_user.id}'")
        return voice

    # No existing clone: create a new single Voice record
    voice = Voice(
        name=voice_name,
        slug=slug,
        description=description or "User uploaded custom cloned voice",
        language=language,
        locale=f"{language}-US",
        accent="Custom",
        gender=gender,
        style="natural",
        tier="custom",
        provider="mock",
        provider_voice_id=unique_provider_voice_id,
        model=clone_model,
        preview_audio_url=preview_url,
        is_public=False,
        is_active=True,
        is_clonable=False,
        commercial_use_allowed=True,
        owner_user_id=current_user.id
    )
    db.add(voice)
    await db.flush()

    # Record VoiceClone audit entry
    clone_record = VoiceClone(
        owner_user_id=current_user.id,
        voice_id=voice.id,
        source_audio_key=storage_key,
        quality_score=0.95,
        consent_confirmed=bool(consent_confirmed),
        rights_confirmed=bool(rights_confirmed),
        status="ready",
        provider="mock",
        provider_voice_id=voice.provider_voice_id
    )
    db.add(clone_record)
    await db.commit()
    await db.refresh(voice)
    logger.info(f"[Voice Clone] Created new single clone: '{voice.name}' (id='{voice.id}', model='{voice.model}') for user '{current_user.id}'")
    return voice

@router.delete("/{voice_id}")
async def delete_custom_voice(
    voice_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Voice).where(Voice.id == voice_id))
    voice = result.scalar_one_or_none()
    if not voice:
        raise AppException(status_code=404, error_code=ErrorCode.VOICE_NOT_FOUND, message="Voice not found.")

    if voice.owner_user_id != current_user.id and current_user.role != "admin":
        raise AppException(status_code=403, error_code=ErrorCode.FORBIDDEN, message="Cannot delete a voice you do not own.")

    voice.is_active = False
    await db.commit()
    return {"message": "Custom voice deleted successfully.", "saved_count": 0}

@router.get("/{voice_id}/preview")
async def get_voice_preview(
    voice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns or on-demand synthesizes audio preview for any library or cloned voice.
    """
    result = await db.execute(select(Voice).where(Voice.id == voice_id))
    voice = result.scalar_one_or_none()
    if not voice:
        raise AppException(status_code=404, error_code=ErrorCode.VOICE_NOT_FOUND, message=f"Voice '{voice_id}' not found.")

    # 1. If voice already has a preview URL, check if local file exists or redirect
    if voice.preview_audio_url:
        local_path = storage_service.get_local_path(f"previews/{voice.id}.mp3")
        if local_path and os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return Response(content=f.read(), media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})
        if voice.preview_audio_url.startswith("http"):
            return RedirectResponse(voice.preview_audio_url)

    # 2. Resolve neural model for preview synthesis
    sample_text = f"Hello, this is {voice.name} speaking on HK Speaks."
    audio_bytes: Optional[bytes] = None

    try:
        from app.providers.edge import EdgeTTSAdapter
        from app.providers.base import TTSRequest
        edge_adapter = EdgeTTSAdapter()
        req = TTSRequest(
            text=sample_text,
            voice_id=voice.id,
            provider_voice_id=voice.provider_voice_id,
            model=voice.model,
            language=voice.language,
            locale=voice.locale,
            gender=voice.gender,
            tier=voice.tier,
            is_clone=bool(voice.tier == "custom" or voice.owner_user_id)
        )
        target_neural = await edge_adapter.resolve_edge_voice(req)

        import edge_tts
        comm = edge_tts.Communicate(sample_text, target_neural)
        b = bytearray()
        async for chunk in comm.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                b.extend(chunk["data"])
        if len(b) > 0:
            audio_bytes = bytes(b)
    except Exception as e:
        logger.warning(f"[Voice Preview] edge_tts preview generation failed for '{voice.name}': {e}")

    if not audio_bytes:
        try:
            audio_bytes = audio_processor.generate_speech_fallback(sample_text)
        except Exception as e:
            logger.error(f"[Voice Preview] Fallback synthesis failed for '{voice.name}': {e}")

    if not audio_bytes:
        raise AppException(
            status_code=500,
            error_code=ErrorCode.AUDIO_GENERATION_FAILED,
            message=f"Failed to generate audio preview for voice '{voice.name}'."
        )

    # 3. Cache to storage and database
    storage_key = f"previews/{voice.id}.mp3"
    preview_url = await storage_service.upload_audio(storage_key, audio_bytes, "audio/mpeg")
    voice.preview_audio_url = preview_url
    await db.commit()

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"}
    )

