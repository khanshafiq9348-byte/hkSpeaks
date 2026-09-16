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

        # Fallback to Unlimited Free Plan
        free_plan = Plan(
            id="default_free_plan",
            name="Unlimited Free",
            slug="unlimited",
            included_characters=999999999,
            included_seconds=9999999,
            allow_cloning=True,
            allow_premium_voices=True,
            allow_api=True,
            allow_commercial_use=True,
            priority=1,
            fair_use_limit=999999999,
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
        Validates whether the user can generate speech.
        All voices (Standard, Premium, Ultra, Edge, ElevenLabs) and lengths are 100% free & unlimited.
        """
        # Private/custom voice check: only ensure user isn't using another user's private clone
        if voice.tier == "custom":
            if voice.owner_user_id and voice.owner_user_id != user.id:
                raise AppException(
                    status_code=403,
                    error_code=ErrorCode.FORBIDDEN,
                    message="You do not have permission to use this custom voice."
                )
        return

    @staticmethod
    async def can_clone_voice(db: AsyncSession, user_id: str) -> bool:
        # Voice cloning is completely free and unlimited
        return True

    @staticmethod
    async def can_use_api(db: AsyncSession, user_id: str) -> bool:
        # Developer API is completely free and unlimited
        return True

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
