from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.entities import User, ApiKey
from app.schemas.api import ApiKeyCreate, ApiKeyResponse, ApiKeyCreatedResponse
from app.security.auth import get_current_user, generate_api_key
from app.services.entitlement import entitlement_service
from app.core.errors import AppException, ErrorCode

router = APIRouter(prefix="/api-keys", tags=["Developer API Keys"])

@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()

@router.post("", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Entitlement check
    can_use_api = await entitlement_service.can_use_api(db, current_user.id)
    if not can_use_api:
        raise AppException(
            status_code=403,
            error_code=ErrorCode.PREMIUM_REQUIRED,
            message="Developer API access requires Starter, Creator, Pro, or Unlimited plan."
        )

    raw_key, prefix, key_hash = generate_api_key()

    key_record = ApiKey(
        user_id=current_user.id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash
    )
    db.add(key_record)
    await db.commit()
    await db.refresh(key_record)

    resp = ApiKeyCreatedResponse(
        id=key_record.id,
        name=key_record.name,
        key_prefix=key_record.key_prefix,
        created_at=key_record.created_at,
        raw_key=raw_key
    )
    return resp

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id))
    key_record = result.scalar_one_or_none()
    if not key_record:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="API key not found.")

    key_record.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "API key revoked successfully."}
