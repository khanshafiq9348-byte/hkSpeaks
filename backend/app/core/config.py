import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "HK Speaks — AI Voice Studio"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_STR: str = "/v1"
    
    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Security
    SECRET_KEY: str = "dev-super-secret-key-for-tts-platform-2026-min32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/tts.db"

    # Redis
    REDIS_URL: str = "memory"

    # Storage
    STORAGE_PROVIDER: str = "local"  # 'local', 's3', 'r2', 'minio'
    STORAGE_LOCAL_DIR: str = "./data/storage"
    STORAGE_PUBLIC_URL_BASE: str = "http://localhost:8000/v1/storage"
    STORAGE_ENDPOINT_URL: Optional[str] = None
    STORAGE_BUCKET_NAME: str = "tts-audio-bucket"
    STORAGE_ACCESS_KEY_ID: Optional[str] = None
    STORAGE_SECRET_ACCESS_KEY: Optional[str] = None
    STORAGE_REGION: str = "auto"

    # TTS Providers
    MOCK_TTS_ENABLED: bool = True
    ELEVENLABS_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Billing & Payments
    PAYMENT_PROVIDER: str = "mock"
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Quotas & Limits
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_AUDIO_DURATION_SECONDS: int = 300
    DEFAULT_CHUNK_SIZE_CHARS: int = 1000

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
