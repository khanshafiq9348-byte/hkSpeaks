import httpx
from typing import List, Dict, Any, Optional
from app.providers.base import TTSProvider, TTSRequest, TTSResult, CostEstimate
from app.core.config import settings
from app.core.errors import AppException, ErrorCode

class OpenAITTSAdapter(TTSProvider):
    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.name = "openai"

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        if not self.api_key:
            raise AppException(
                status_code=503,
                error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                message="OpenAI API key is not configured."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Model mapping: tts-1 or tts-1-hd
        model = "tts-1-hd" if request.model == "ultra" else "tts-1"
        payload = {
            "model": model,
            "input": request.text,
            "voice": request.provider_voice_id or "alloy",
            "response_format": request.format if request.format in ["mp3", "wav", "aac", "flac"] else "mp3",
            "speed": request.speed
        }
        url = f"{self.BASE_URL}/audio/speech"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise AppException(
                    status_code=502,
                    error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message=f"OpenAI TTS synthesis error ({resp.status_code}): {resp.text[:200]}"
                )

            audio_bytes = resp.content
            duration = max(1.0, len(request.text) / (15.0 * request.speed))

            return TTSResult(
                audio_bytes=audio_bytes,
                provider_request_id=resp.headers.get("x-request-id", "openai_gen"),
                duration_seconds=round(duration, 2),
                format=payload["response_format"],
                metadata={"provider": "openai", "model": model}
            )

    async def get_voices(self) -> List[Dict[str, Any]]:
        # OpenAI standard voice list
        return [
            {"id": "alloy", "name": "Alloy", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "gender": "male"},
            {"id": "fable", "name": "Fable", "gender": "neutral"},
            {"id": "onyx", "name": "Onyx", "gender": "male"},
            {"id": "nova", "name": "Nova", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female"}
        ]

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.BASE_URL}/models", headers=headers)
                return resp.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, request: TTSRequest) -> CostEstimate:
        # OpenAI tts-1 is $0.015 / 1,000 characters ($0.000015/char), tts-1-hd is $0.030 / 1,000 characters ($0.000030/char)
        chars = len(request.text)
        rate = 0.000030 if request.model == "ultra" else 0.000015
        return CostEstimate(
            currency="USD",
            estimated_amount=round(chars * rate, 6),
            pricing_unit="characters"
        )
