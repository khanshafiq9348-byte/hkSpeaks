from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health():
    return {"status": "ok", "service": "tts-platform-api"}

@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    try:
        # Check DB connectivity
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE
