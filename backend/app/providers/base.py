from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class TTSRequest(BaseModel):
    text: str
    voice_id: str
    provider_voice_id: str
    language: str = "en"
    locale: str = "en-US"
    gender: Optional[str] = None
    model: str = "standard-v1"
    speed: float = 1.0
    pitch: float = 0.0
    style: float = 0.0
    stability: float = 0.5
    similarity: float = 0.75
    format: str = "mp3"  # mp3 or wav
    sample_rate: int = 44100
    tier: Optional[str] = None
    is_clone: bool = False

class TTSResult(BaseModel):
    audio_bytes: bytes
    provider_request_id: str
    duration_seconds: float
    format: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CostEstimate(BaseModel):
    currency: str = "USD"
    estimated_amount: float
    pricing_unit: str = "characters"

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Synthesize text into speech audio bytes."""
        raise NotImplementedError

    @abstractmethod
    async def get_voices(self) -> List[Dict[str, Any]]:
        """Retrieve available voices from provider."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if provider is responsive and operational."""
        raise NotImplementedError

    @abstractmethod
    def estimate_cost(self, request: TTSRequest) -> CostEstimate:
        """Estimate provider compute cost for the given request."""
        raise NotImplementedError
