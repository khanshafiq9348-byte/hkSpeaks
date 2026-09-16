from typing import List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.entities import User, Plan, Subscription, CreditLedger, Generation, Payment
from app.schemas.api import PlanResponse, SubscriptionResponse, UsageSummaryResponse
from app.security.auth import get_current_user
from app.services.entitlement import entitlement_service
from app.core.errors import AppException, ErrorCode

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions"])

@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.active == True).order_by(Plan.priority.asc()))
    plans = result.scalars().all()
    return plans

@router.get("/subscription")
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    plan, subscription = await entitlement_service.get_user_plan_and_subscription(db, current_user.id)
    return {
        "plan": plan,
        "subscription": subscription,
        "status": subscription.status if subscription else "active",
        "is_custom": plan.slug == "enterprise"
    }

@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    plan, _ = await entitlement_service.get_user_plan_and_subscription(db, current_user.id)
    chars_used = await entitlement_service.get_character_usage_this_period(db, current_user.id)
    limit = plan.fair_use_limit if plan.slug == "unlimited" else plan.included_characters
    chars_remaining = max(0, limit - chars_used)

    # Get seconds used and generations count
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    sec_res = await db.execute(
        select(func.coalesce(func.sum(Generation.actual_audio_seconds), 0.0), func.count(Generation.id))
        .where(
            Generation.user_id == current_user.id,
            Generation.status == "completed",
            Generation.created_at >= start_of_month
        )
    )
    seconds_used, gen_count = sec_res.first()

    # Fair use status calculation
    fair_use = "healthy"
    if plan.slug == "unlimited":
        if chars_used > plan.fair_use_limit * 0.9:
            fair_use = "warning"
        if chars_used >= plan.fair_use_limit:
            fair_use = "throttled"

    return UsageSummaryResponse(
        plan_name=plan.name,
        plan_slug=plan.slug,
        characters_used=chars_used,
        characters_limit=limit,
        characters_remaining=chars_remaining,
        seconds_used=round(float(seconds_used or 0.0), 1),
        generations_count=int(gen_count or 0),
        fair_use_status=fair_use,
        can_clone=plan.allow_cloning,
        can_use_premium=plan.allow_premium_voices,
        can_use_api=plan.allow_api
    )

@router.post("/upgrade")
async def upgrade_plan(
    plan_slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    plan_res = await db.execute(select(Plan).where(Plan.slug == plan_slug, Plan.active == True))
    target_plan = plan_res.scalar_one_or_none()
    if not target_plan:
        raise AppException(status_code=404, error_code=ErrorCode.NOT_FOUND, message="Plan not found.")

    # Update or create subscription
    sub_res = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = sub_res.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    if sub:
        sub.plan_id = target_plan.id
        sub.status = "active"
        sub.current_period_start = now
        sub.current_period_end = period_end
    else:
        sub = Subscription(
            user_id=current_user.id,
            plan_id=target_plan.id,
            status="active",
            current_period_start=now,
            current_period_end=period_end
        )
        db.add(sub)

    # Record payment
    payment = Payment(
        user_id=current_user.id,
        provider="mock",
        provider_payment_id=f"pay_{now.timestamp()}",
        amount=target_plan.monthly_price,
        currency=target_plan.currency,
        status="succeeded",
        metadata_json={"plan": target_plan.slug}
    )
    db.add(payment)

    # Grant new credits in ledger
    grant = CreditLedger(
        user_id=current_user.id,
        transaction_type="subscription_grant",
        units=target_plan.included_characters,
        reference_type="subscription",
        reference_id=sub.id,
        description=f"Monthly grant for {target_plan.name}"
    )
    db.add(grant)
    await db.commit()

    return {
        "success": True,
        "message": f"Successfully upgraded to {target_plan.name}!",
        "plan": target_plan.name
    }
