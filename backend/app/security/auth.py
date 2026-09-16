import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt
import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppException, ErrorCode
from app.db.session import get_db
from app.models.entities import User, ApiKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def generate_api_key() -> Tuple[str, str, str]:
    """
    Returns:
    (raw_key, prefix, hash)
    Format: hk_live_<32_random_bytes_hex>
    """
    prefix = "hk_live_"
    random_part = secrets.token_hex(24)
    raw_key = f"{prefix}{random_part}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, prefix, key_hash

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

async def get_current_user_from_token(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Supports either JWT Bearer token or API Key Bearer token.
    """
    if not authorization:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_REQUIRED,
            message="Missing Authorization header."
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_REQUIRED,
            message="Invalid Authorization format. Expected 'Bearer <token>'."
        )

    # Check if this is an API key (starts with hk_live_)
    if token.startswith("hk_live_"):
        key_hash = hash_api_key(token)
        result = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code=ErrorCode.AUTH_REQUIRED,
                message="Invalid or revoked API key."
            )
        
        # Update last used
        api_key.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        user_result = await db.execute(select(User).where(User.id == api_key.user_id))
        user = user_result.scalar_one_or_none()
        if not user or user.status != "active":
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code=ErrorCode.FORBIDDEN,
                message="User account associated with this API key is inactive."
            )
        return user

    # Otherwise treat as JWT
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_REQUIRED,
            message="Invalid or expired access token."
        )
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_REQUIRED,
            message="User not found or inactive."
        )
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "admin":
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.FORBIDDEN,
            message="Administrative privileges required."
        )
    return current_user

async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization=authorization, db=db)
    except Exception:
        return None

async def get_current_user_or_default(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Returns authenticated user if token present; otherwise resolves default system/admin user.
    Enables seamless interaction from UI workspaces and automated queue runners.
    """
    if authorization:
        try:
            return await get_current_user(authorization=authorization, db=db)
        except Exception:
            pass
    # Fallback to active creator user or first active user
    result = await db.execute(
        select(User).where(User.email == "creator@hkspeaks.ai", User.status == "active")
    )
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.status == "active").order_by(User.created_at.asc()).limit(1))
        user = result.scalar_one_or_none()
    if not user:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_REQUIRED,
            message="No active user found in system."
        )
    return user

