import httpx
from typing import List, Dict, Any, Optional
from app.providers.base import TTSProvider, TTSRequest, TTSResult, CostEstimate
from app.core.config import settings
from app.core.errors import AppException, ErrorCode

class ElevenLabsAdapter(TTSProvider):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.name = "elevenlabs"

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        if not self.api_key:
            raise AppException(
                status_code=503,
                error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                message="ElevenLabs API key is not configured."
            )

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg" if request.format == "mp3" else "audio/wav"
        }
        payload = {
            "text": request.text,
            "model_id": request.model if request.model.startswith("eleven_") else "eleven_multilingual_v2",
            "voice_settings": {
                "stability": request.stability,
                "similarity_boost": request.similarity,
                "style": request.style
            }
        }
        url = f"{self.BASE_URL}/text-to-speech/{request.provider_voice_id}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise AppException(
                    status_code=502,
                    error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message=f"ElevenLabs synthesis error ({resp.status_code}): {resp.text[:200]}"
                )
            
            audio_bytes = resp.content
            # Estimate duration based on content length
            duration = max(1.0, len(request.text) / 15.0)

            return TTSResult(
                audio_bytes=audio_bytes,
                provider_request_id=resp.headers.get("request-id", "el_gen"),
                duration_seconds=round(duration, 2),
                format=request.format,
                metadata={"provider": "elevenlabs", "model": payload["model_id"]}
            )

    async def get_voices(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        headers = {"xi-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.BASE_URL}/voices", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("voices", [])
        return []

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"xi-api-key": self.api_key}
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.BASE_URL}/user", headers=headers)
                return resp.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, request: TTSRequest) -> CostEstimate:
        # ElevenLabs Creator tier roughly $0.00003 per character
        chars = len(request.text)
        return CostEstimate(
            currency="USD",
            estimated_amount=round(chars * 0.00003, 6),
            pricing_unit="characters"
        )
