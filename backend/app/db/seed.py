import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import async_session_maker, engine
from app.db.base_class import Base
from app.models.entities import User, Plan, Subscription, Voice, Project, ProjectDocument, CreditLedger
import app.models.video_entities  # Ensure all video models are registered with Base.metadata
import app.models.prompt_entities  # Ensure all audio prompt models are registered with Base.metadata
import app.models.bulk_image_entities  # Ensure all bulk image models are registered with Base.metadata
from app.security.auth import hash_password

async def seed_data():
    async with engine.begin() as conn:
        # Create all tables if not created
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as db:
        # 1. Seed Plans
        plans_data = [
            {
                "name": "Free",
                "slug": "free",
                "description": "Essential voices for hobbyists and experimentation.",
                "monthly_price": 0.0,
                "included_characters": 10000,
                "included_seconds": 300,
                "allow_cloning": False,
                "allow_premium_voices": False,
                "allow_api": False,
                "allow_commercial_use": False,
                "priority": 1,
                "fair_use_limit": 15000,
                "active": True
            },
            {
                "name": "Starter",
                "slug": "starter",
                "description": "Commercial license & API access for indie builders.",
                "monthly_price": 9.0,
                "included_characters": 50000,
                "included_seconds": 1500,
                "allow_cloning": False,
                "allow_premium_voices": False,
                "allow_api": True,
                "allow_commercial_use": True,
                "priority": 2,
                "fair_use_limit": 60000,
                "active": True
            },
            {
                "name": "Creator",
                "slug": "creator",
                "description": "Premium voices & custom voice cloning for content creators.",
                "monthly_price": 29.0,
                "included_characters": 250000,
                "included_seconds": 8000,
                "allow_cloning": True,
                "allow_premium_voices": True,
                "allow_api": True,
                "allow_commercial_use": True,
                "priority": 3,
                "fair_use_limit": 300000,
                "active": True
            },
            {
                "name": "Pro",
                "slug": "pro",
                "description": "Ultra high-fidelity voices and higher throughput.",
                "monthly_price": 79.0,
                "included_characters": 1000000,
                "included_seconds": 30000,
                "allow_cloning": True,
                "allow_premium_voices": True,
                "allow_api": True,
                "allow_commercial_use": True,
                "priority": 4,
                "fair_use_limit": 1200000,
                "active": True
            },
            {
                "name": "Unlimited",
                "slug": "unlimited",
                "description": "Fair-use unlimited generation for power studios and businesses.",
                "monthly_price": 149.0,
                "included_characters": 5000000,
                "included_seconds": 150000,
                "allow_cloning": True,
                "allow_premium_voices": True,
                "allow_api": True,
                "allow_commercial_use": True,
                "priority": 5,
                "fair_use_limit": 5000000,
                "active": True
            }
        ]

        plans_by_slug = {}
        for pdata in plans_data:
            res = await db.execute(select(Plan).where(Plan.slug == pdata["slug"]))
            plan = res.scalar_one_or_none()
            if not plan:
                plan = Plan(**pdata)
                db.add(plan)
                await db.flush()
            plans_by_slug[pdata["slug"]] = plan

        # 2. Seed Voices
        voices_data = [
            {
                "name": "Sarah (Natural Storyteller)",
                "slug": "sarah-storyteller",
                "description": "Warm, engaging female voice perfect for narratives, audiobooks, and explainers.",
                "language": "en",
                "locale": "en-US",
                "accent": "American",
                "gender": "female",
                "style": "Storytelling, Narration",
                "tier": "free",
                "provider": "mock",
                "provider_voice_id": "sarah",
                "model": "standard-v1",
                "is_public": True,
                "commercial_use_allowed": True
            },
            {
                "name": "David (Authoritative News)",
                "slug": "david-news",
                "description": "Confident, broadcast-ready male voice built for news segments and corporate presentations.",
                "language": "en",
                "locale": "en-US",
                "accent": "American",
                "gender": "male",
                "style": "News, Educational",
                "tier": "free",
                "provider": "mock",
                "provider_voice_id": "david",
                "model": "standard-v1",
                "is_public": True,
                "commercial_use_allowed": True
            },
            {
                "name": "Marcus (Deep Documentary)",
                "slug": "marcus-documentary",
                "description": "Rich, resonant British documentary narration with dramatic weight.",
                "language": "en",
                "locale": "en-GB",
                "accent": "British",
                "gender": "male",
                "style": "Documentary, Cinematic, Narration",
                "tier": "premium",
                "provider": "mock",
                "provider_voice_id": "marcus",
                "model": "premium-v2",
                "is_public": True,
                "commercial_use_allowed": True
            },
            {
                "name": "Elena (Energetic Commercial)",
                "slug": "elena-commercial",
                "description": "Dynamic, vibrant commercial voice tailored for high-converting ads and social promos.",
                "language": "en",
                "locale": "en-US",
                "accent": "American",
                "gender": "female",
                "style": "Commercial, Conversational",
                "tier": "ultra",
                "provider": "mock",
                "provider_voice_id": "elena",
                "model": "ultra-v3",
                "is_public": True,
                "commercial_use_allowed": True
            },
            {
                "name": "Alexander (Calm Audiobook)",
                "slug": "alexander-audiobook",
                "description": "Introspective, soothing pacing designed for long-form fiction and guided meditation.",
                "language": "en",
                "locale": "en-US",
                "accent": "American",
                "gender": "male",
                "style": "Storytelling, Narration",
                "tier": "premium",
                "provider": "mock",
                "provider_voice_id": "alexander",
                "model": "premium-v2",
                "is_public": True,
                "commercial_use_allowed": True
            },
            {
                "name": "Chloe (Conversational)",
                "slug": "chloe-conversational",
                "description": "Casual, friendly tone with natural pacing for modern podcasts and video essays.",
                "language": "en",
                "locale": "en-AU",
                "accent": "Australian",
                "gender": "female",
                "style": "Conversational, Educational",
                "tier": "free",
                "provider": "mock",
                "provider_voice_id": "chloe",
                "model": "standard-v1",
                "is_public": True,
                "commercial_use_allowed": True
            }
        ]

        for vdata in voices_data:
            res = await db.execute(select(Voice).where(Voice.slug == vdata["slug"]))
            if not res.scalar_one_or_none():
                v = Voice(**vdata)
                db.add(v)

        # 2b. Seed Authentic Provider Voice Catalog (1000+ real voices)
        try:
            from app.db.voice_catalog import AUTHENTIC_VOICE_CATALOG
            existing_slugs_res = await db.execute(select(Voice.slug))
            existing_slugs = set(existing_slugs_res.scalars().all())
            for av in AUTHENTIC_VOICE_CATALOG:
                if av["slug"] not in existing_slugs:
                    db.add(Voice(**av))
                    existing_slugs.add(av["slug"])
        except Exception as e:
            logger.warning(f"Failed to seed authentic voice catalog: {e}")

        # 3. Seed Admin User
        admin_res = await db.execute(select(User).where(User.email == "admin@hkspeaks.ai"))
        admin_user = admin_res.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                email="admin@hkspeaks.ai",
                hashed_password=hash_password("AdminPass123!"),
                display_name="HK Speaks Admin",
                role="admin",
                status="active"
            )
            db.add(admin_user)
            await db.flush()

            # Admin gets Unlimited Plan
            admin_sub = Subscription(
                user_id=admin_user.id,
                plan_id=plans_by_slug["unlimited"].id,
                status="active"
            )
            db.add(admin_sub)
            db.add(CreditLedger(
                user_id=admin_user.id,
                transaction_type="subscription_grant",
                units=plans_by_slug["unlimited"].included_characters,
                description="Unlimited admin subscription grant"
            ))

        # 4. Seed Demo Creator User
        creator_res = await db.execute(select(User).where(User.email == "creator@hkspeaks.ai"))
        creator_user = creator_res.scalar_one_or_none()
        if not creator_user:
            creator_user = User(
                email="creator@hkspeaks.ai",
                hashed_password=hash_password("CreatorPass123!"),
                display_name="Demo Creator",
                role="user",
                status="active"
            )
            db.add(creator_user)
            await db.flush()

            # Creator gets Creator Plan
            creator_sub = Subscription(
                user_id=creator_user.id,
                plan_id=plans_by_slug["creator"].id,
                status="active"
            )
            db.add(creator_sub)
            db.add(CreditLedger(
                user_id=creator_user.id,
                transaction_type="subscription_grant",
                units=plans_by_slug["creator"].included_characters,
                description="Creator subscription grant"
            ))

            # Add demo project
            proj = Project(
                owner_user_id=creator_user.id,
                name="AI Documentary: The Dawn of Synthesis",
                description="A mini-documentary script examining the history and evolution of vocal modeling."
            )
            db.add(proj)
            await db.flush()

            doc = ProjectDocument(
                project_id=proj.id,
                title="Scene 1: Introduction",
                content="Deep within the silicon circuits of modern neural networks, a quiet revolution has taken place. Speech—once the unique signature of the human vocal tract—is now rendered with astonishing fidelity by mathematics and acoustic modeling.",
                language="en"
            )
            db.add(doc)

        # Migrate any voices with outdated or unstable neural models
        from sqlalchemy import update
        await db.execute(
            update(Voice)
            .where(Voice.model == "en-GB-ThomasNeural")
            .values(model="en-US-AndrewNeural")
        )
        await db.execute(
            update(Voice)
            .where(Voice.model == "en-US-JaneNeural")
            .values(model="en-US-AvaNeural")
        )

        await db.commit()
        print("Database seeded successfully with plans, voices, and demo accounts!")

if __name__ == "__main__":
    asyncio.run(seed_data())
