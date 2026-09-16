from typing import Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.entities import User, Subscription, Plan, Generation, CreditLedger, Voice
from app.core.errors import AppException, ErrorCode

class EntitlementService:
    @staticmethod
    async def get_user_plan_and_subscription(db: AsyncSession, user_id: str) -> Tuple[Plan, Optional[Subscription]]:
        """
        Retrieves active subscription plan, or defaults to the Free plan.
        """
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            plan_result = await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
            plan = plan_result.scalar_one_or_none()
            if plan:
                return plan, subscription

        # Fallback to Free Plan
        free_plan_result = await db.execute(select(Plan).where(Plan.slug == "free"))
        free_plan = free_plan_result.scalar_one_or_none()
        if not free_plan:
            # Dynamically construct if not yet seeded
            free_plan = Plan(
                id="default_free_plan",
                name="Free Starter",
                slug="free",
                included_characters=10000,
                included_seconds=300,
                allow_cloning=False,
                allow_premium_voices=False,
                allow_api=False,
                allow_commercial_use=False,
                priority=1,
                fair_use_limit=15000,
                active=True
            )
        return free_plan, None

    @staticmethod
    async def get_character_usage_this_period(db: AsyncSession, user_id: str) -> int:
        """
        Calculates character usage in current billing cycle or month.
        """
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await db.execute(
            select(func.coalesce(func.sum(Generation.input_characters), 0))
            .where(
                Generation.user_id == user_id,
                Generation.status.in_(["completed", "processing", "queued"]),
                Generation.created_at >= start_of_month
            )
        )
        return int(result.scalar_one() or 0)

    @staticmethod
    async def check_can_generate(
        db: AsyncSession,
        user: User,
        voice: Voice,
        text_length: int
    ):
        """
        Validates whether the user can generate speech for the requested voice and text length.
        """
        plan, _ = await EntitlementService.get_user_plan_and_subscription(db, user.id)

        # 1. Voice tier entitlement check
        if voice.tier in ["premium", "ultra"] and not plan.allow_premium_voices:
            raise AppException(
                status_code=403,
                error_code=ErrorCode.PREMIUM_REQUIRED,
                message=f"Voice '{voice.name}' is a {voice.tier.capitalize()} voice. Please upgrade your subscription to access premium voices.",
                details={"required_tier": voice.tier, "current_plan": plan.name}
            )

        # 2. Private/custom voice entitlement check
        if voice.tier == "custom":
            if voice.owner_user_id != user.id:
                raise AppException(
                    status_code=403,
                    error_code=ErrorCode.FORBIDDEN,
                    message="You do not have permission to use this custom voice."
                )

        # 3. Quota / Fair-use check
        current_chars = await EntitlementService.get_character_usage_this_period(db, user.id)
        limit = plan.fair_use_limit if plan.slug == "unlimited" else plan.included_characters

        if current_chars + text_length > limit:
            raise AppException(
                status_code=402,
                error_code=ErrorCode.QUOTA_EXCEEDED,
                message=f"Character quota exceeded. Plan limit is {limit:,} characters, currently used {current_chars:,}.",
                details={
                    "current_usage": current_chars,
                    "request_chars": text_length,
                    "limit": limit,
                    "plan": plan.name
                }
            )

    @staticmethod
    async def can_clone_voice(db: AsyncSession, user_id: str) -> bool:
        # Every user has access to 1 private cloned voice slot
        return True

    @staticmethod
    async def can_use_api(db: AsyncSession, user_id: str) -> bool:
        plan, _ = await EntitlementService.get_user_plan_and_subscription(db, user_id)
        return plan.allow_api

    @staticmethod
    async def reserve_credit(db: AsyncSession, user_id: str, generation_id: str, characters: int):
        """
        Creates a credit reservation ledger entry.
        """
        ledger = CreditLedger(
            user_id=user_id,
            transaction_type="generation_reservation",
            units=-characters,
            reference_type="generation",
            reference_id=generation_id,
            description=f"Reserved {characters} characters for generation {generation_id}"
        )
        db.add(ledger)
        await db.commit()

    @staticmethod
    async def finalize_usage(db: AsyncSession, user_id: str, generation_id: str, characters: int):
        """
        Converts reservation into permanent debit.
        """
        ledger = CreditLedger(
            user_id=user_id,
            transaction_type="generation_debit",
            units=-characters,
            reference_type="generation",
            reference_id=generation_id,
            description=f"Debited {characters} characters for completed generation {generation_id}"
        )
        db.add(ledger)
        await db.commit()

    @staticmethod
    async def refund_reservation(db: AsyncSession, user_id: str, generation_id: str, characters: int, reason: str = "Generation failed"):
        """
        Releases/refunds reserved credits if generation failed or was cancelled.
        """
        ledger = CreditLedger(
            user_id=user_id,
            transaction_type="refund",
            units=characters,
            reference_type="generation",
            reference_id=generation_id,
            description=f"Refunded {characters} characters: {reason}"
        )
        db.add(ledger)
        await db.commit()

entitlement_service = EntitlementService()
