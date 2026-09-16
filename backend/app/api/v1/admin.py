from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.models.entities import User, Generation, Subscription, Payment, Voice
from app.schemas.api import AdminStatsResponse, UserResponse, GenerationResponse
from app.security.auth import get_current_admin_user
from app.providers.router import tts_router

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    users_count = await db.execute(select(func.count(User.id)))
    gens_count = await db.execute(select(func.count(Generation.id)))
    chars_count = await db.execute(select(func.coalesce(func.sum(Generation.input_characters), 0)))
    secs_count = await db.execute(select(func.coalesce(func.sum(Generation.actual_audio_seconds), 0.0)))
    subs_count = await db.execute(select(func.count(Subscription.id)).where(Subscription.status == "active"))
    failed_count = await db.execute(select(func.count(Generation.id)).where(Generation.status == "failed"))
    cost_res = await db.execute(select(func.coalesce(func.sum(Generation.estimated_cost), 0.0)))
    rev_res = await db.execute(select(func.coalesce(func.sum(Payment.amount), 0.0)))

    return AdminStatsResponse(
        total_users=users_count.scalar_one(),
        total_generations=gens_count.scalar_one(),
        total_characters_generated=chars_count.scalar_one(),
        total_audio_seconds=round(secs_count.scalar_one(), 1),
        active_subscriptions=subs_count.scalar_one(),
        total_revenue_estimate=round(rev_res.scalar_one(), 2),
        provider_cost_estimate=round(cost_res.scalar_one(), 4),
        failed_jobs_count=failed_count.scalar_one()
    )

@router.get("/users", response_model=List[UserResponse])
async def list_admin_users(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).order_by(desc(User.created_at)).limit(100))
    return result.scalars().all()

@router.get("/generations", response_model=List[GenerationResponse])
async def list_admin_generations(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Generation).order_by(desc(Generation.created_at)).limit(50))
    gens = result.scalars().all()
    resp = []
    for g in gens:
        v_res = await db.execute(select(Voice).where(Voice.id == g.voice_id))
        voice = v_res.scalar_one_or_none()
        r = GenerationResponse.model_validate(g)
        if voice:
            r.voice_name = voice.name
        resp.append(r)
    return resp

@router.get("/providers")
async def get_providers_health(
    admin_user: User = Depends(get_current_admin_user)
):
    health = await tts_router.get_all_provider_health()
    return {
        "providers": [
            {
                "name": name,
                "status": "healthy" if status else "unavailable",
                "is_fallback": name == "mock"
            }
            for name, status in health.items()
        ]
    }
