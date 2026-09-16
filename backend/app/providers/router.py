from typing import Dict, Optional, List, Any
import logging
from app.providers.base import TTSProvider, TTSRequest, TTSResult, CostEstimate
from app.providers.mock import MockTTSProvider
from app.providers.elevenlabs import ElevenLabsAdapter
from app.providers.openai import OpenAITTSAdapter
from app.providers.edge import EdgeTTSAdapter
from app.core.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)

class TTSRouter:
    def __init__(self):
        edge_adapter = EdgeTTSAdapter()
        self.providers: Dict[str, TTSProvider] = {
            "mock": MockTTSProvider("mock"),
            "edge": edge_adapter,
            "azure": edge_adapter,
            "amazon": edge_adapter,
            "google": edge_adapter,
            "elevenlabs": ElevenLabsAdapter(),
            "openai": OpenAITTSAdapter(),
        }
        self.fallback_provider = edge_adapter

    def register_provider(self, name: str, provider: TTSProvider):
        self.providers[name] = provider

    def get_provider(self, name: str) -> TTSProvider:
        return self.providers.get(name.lower(), self.fallback_provider)

    async def synthesize(self, request: TTSRequest, preferred_provider: str = "mock") -> TTSResult:
        primary = self.get_provider(preferred_provider)
        
        try:
            # Attempt primary provider
            return await primary.synthesize(request)
        except Exception as e:
            logger.warning(
                f"Primary TTS provider '{preferred_provider}' failed for voice '{request.voice_id}': {e}"
            )
            # Never fallback for cloned voices! Protect exact voice identity.
            if request.is_clone or (request.tier and request.tier.lower() == "custom"):
                logger.error(
                    f"Voice '{request.voice_id}' is a cloned voice. Strict identity rule prohibits provider fallback."
                )
                raise

            # Failover to mock provider for standard voices if configured and primary was not mock
            if preferred_provider != "mock":
                try:
                    result = await self.fallback_provider.synthesize(request)
                    result.metadata["fallback_from"] = preferred_provider
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
                    raise AppException(
                        status_code=500,
                        error_code=ErrorCode.GENERATION_FAILED,
                        message=f"TTS generation failed: {str(e)}"
                    )
            raise

    def estimate_cost(self, request: TTSRequest, provider_name: str = "mock") -> CostEstimate:
        provider = self.get_provider(provider_name)
        return provider.estimate_cost(request)

    async def get_all_provider_health(self) -> Dict[str, bool]:
        health = {}
        for name, provider in self.providers.items():
            try:
                health[name] = await provider.health_check()
            except Exception:
                health[name] = False
        return health

tts_router = TTSRouter()
