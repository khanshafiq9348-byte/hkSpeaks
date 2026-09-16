import pytest
import asyncio
import os
import tempfile
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base_class import Base
from app.db.session import get_db
from app.main import app
from app.db.seed import seed_data

TEST_DB_FILE = tempfile.mktemp(suffix=".db")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30.0}
)

test_session_maker = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def override_get_db():
    async with test_session_maker() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    import app.models.entities
    import app.models.video_entities

    async with test_engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA busy_timeout=30000;"))
        await conn.run_sync(Base.metadata.create_all)
    
    # Run seed data in test DB
    from app.db import seed
    from app.workers import processor, video_processor
    orig_engine = seed.engine
    orig_session_maker = seed.async_session_maker
    orig_proc_maker = processor.async_session_maker
    orig_vid_maker = video_processor.async_session_maker
    seed.engine = test_engine
    seed.async_session_maker = test_session_maker
    processor.async_session_maker = test_session_maker
    video_processor.async_session_maker = test_session_maker
    await seed_data()
    seed.engine = orig_engine
    seed.async_session_maker = orig_session_maker

    yield

    processor.async_session_maker = orig_proc_maker
    video_processor.async_session_maker = orig_vid_maker

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
