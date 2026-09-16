from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from app.db.session import get_db
from app.models.entities import User, Plan, Subscription, CreditLedger
from app.schemas.api import UserSignup, UserLogin, TokenResponse, UserResponse
from app.security.auth import hash_password, verify_password, create_access_token, get_current_user
from app.core.errors import AppException, ErrorCode

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse)
async def signup(body: UserSignup, db: AsyncSession = Depends(get_db)):
    # Check existing user
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise AppException(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="An account with this email already exists."
        )

    # Check if first user, assign admin
    count_res = await db.execute(select(User))
    first_user = count_res.first() is None
    role = "admin" if first_user else "user"

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        role=role,
        status="active"
    )
    db.add(user)
    await db.flush()

    # Assign default free plan
    free_plan_res = await db.execute(select(Plan).where(Plan.slug == "free"))
    free_plan = free_plan_res.scalar_one_or_none()
    if free_plan:
        sub = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active"
        )
        db.add(sub)
        # Grant initial character allocation
        ledger = CreditLedger(
            user_id=user.id,
            transaction_type="subscription_grant",
            units=free_plan.included_characters,
            description="Initial free plan grant"
        )
        db.add(ledger)

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise AppException(
            status_code=401,
            error_code=ErrorCode.AUTH_REQUIRED,
            message="Invalid email or password."
        )
    if user.status != "active":
        raise AppException(
            status_code=403,
            error_code=ErrorCode.FORBIDDEN,
            message="Account is suspended or inactive."
        )

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
