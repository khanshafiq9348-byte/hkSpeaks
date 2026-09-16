import os
import uuid
import tempfile
import logging
from typing import List, Dict, Any, Optional
import edge_tts

from app.providers.base import TTSProvider, TTSRequest, TTSResult, CostEstimate
from app.core.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)

_VALID_EDGE_VOICES = None

COMMON_EDGE_FALLBACKS = {
    ("en", "male"): "en-US-GuyNeural",
    ("en", "female"): "en-US-JennyNeural",
    ("es", "male"): "es-ES-AlvaroNeural",
    ("es", "female"): "es-ES-ElviraNeural",
    ("fr", "male"): "fr-FR-HenriNeural",
    ("fr", "female"): "fr-FR-DeniseNeural",
    ("de", "male"): "de-DE-KillianNeural",
    ("de", "female"): "de-DE-KatjaNeural",
    ("hi", "male"): "hi-IN-MadhurNeural",
    ("hi", "female"): "hi-IN-SwaraNeural",
    ("it", "male"): "it-IT-DiegoNeural",
    ("it", "female"): "it-IT-ElsaNeural",
    ("ja", "male"): "ja-JP-KeitaNeural",
    ("ja", "female"): "ja-JP-NanamiNeural",
    ("zh", "male"): "zh-CN-YunxiNeural",
    ("zh", "female"): "zh-CN-XiaoxiaoNeural",
    ("ar", "male"): "ar-SA-HamedNeural",
    ("ar", "female"): "ar-SA-ZariyahNeural",
    ("pt", "male"): "pt-BR-AntonioNeural",
    ("pt", "female"): "pt-BR-FranciscaNeural",
    ("ru", "male"): "ru-RU-DmitryNeural",
    ("ru", "female"): "ru-RU-SvetlanaNeural",
    ("ko", "male"): "ko-KR-InJoonNeural",
    ("ko", "female"): "ko-KR-SunHiNeural",
    ("nl", "male"): "nl-NL-MaartenNeural",
    ("nl", "female"): "nl-NL-FennaNeural",
}

class EdgeTTSAdapter(TTSProvider):
    def __init__(self):
        self.name = "edge"

    async def _get_valid_voices(self) -> Dict[str, Any]:
        global _VALID_EDGE_VOICES
        if _VALID_EDGE_VOICES is None:
            try:
                v_list = await edge_tts.list_voices()
                _VALID_EDGE_VOICES = {v["ShortName"]: v for v in v_list}
            except Exception as e:
                logger.warning(f"Failed to fetch edge_tts voice list: {e}")
                _VALID_EDGE_VOICES = {}
        return _VALID_EDGE_VOICES

    async def resolve_edge_voice(self, request: TTSRequest) -> str:
        valid_voices = await self._get_valid_voices()

        # 1. For cloned voices, use the assigned clone model timbre directly!
        if request.is_clone or (request.tier and request.tier.lower() == "custom"):
            for candidate in [request.model, request.provider_voice_id]:
                if candidate and candidate in valid_voices:
                    return candidate
            return "en-GB-LibbyNeural"

        # 2. Direct match with valid Edge shortnames
        p_id = request.provider_voice_id or ""
        if p_id in valid_voices:
            return p_id

        if request.model and request.model in valid_voices:
            return request.model

        # 3. Known named map
        voice_map = {
            "sarah": "en-US-JennyNeural",
            "david": "en-US-GuyNeural",
            "marcus": "en-GB-RyanNeural",
            "elena": "en-US-AriaNeural",
            "alexander": "en-US-ChristopherNeural",
            "chloe": "en-AU-NatashaNeural"
        }
        if p_id.lower() in voice_map:
            return voice_map[p_id.lower()]

        # 4. Match by exact locale and gender
        target_gender = "Male" if (request.gender or "").lower() == "male" else "Female"
        if request.locale:
            for sn, v in valid_voices.items():
                if v.get("Locale", "").lower() == request.locale.lower() and v.get("Gender", "").lower() == target_gender.lower():
                    return sn

        # 5. Match by language and gender
        lang = (request.language or "en").lower().split("-")[0]
        for sn, v in valid_voices.items():
            if v.get("Locale", "").lower().startswith(f"{lang}-") and v.get("Gender", "").lower() == target_gender.lower():
                return sn

        # 6. Fallback from common dictionary
        fallback = COMMON_EDGE_FALLBACKS.get((lang, "male" if target_gender == "Male" else "female"))
        if fallback:
            return fallback

        return "en-US-GuyNeural" if target_gender == "Male" else "en-US-JennyNeural"

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        voice_id = await self.resolve_edge_voice(request)
        if request.is_clone or (request.tier and request.tier.lower() == "custom"):
            logger.info(f"[Edge TTS Cloned Voice] Synthesizing cloned voice '{request.voice_id}' using timbre model '{voice_id}'")
        else:
            logger.info(f"[Edge TTS Library Voice] Synthesizing library voice '{request.voice_id}' using provider voice '{voice_id}'")

        rate_pct = int(round((request.speed - 1.0) * 100))
        rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"

        pitch_hz = int(round(request.pitch * 5))
        pitch_str = f"{pitch_hz:+d}Hz" if pitch_hz != 0 else "+0Hz"

        temp_dir = tempfile.gettempdir()
        temp_mp3 = os.path.join(temp_dir, f"edge_out_{uuid.uuid4().hex[:8]}.mp3")
        try:
            communicate = edge_tts.Communicate(
                text=request.text,
                voice=voice_id,
                rate=rate_str,
                pitch=pitch_str
            )
            await communicate.save(temp_mp3)

            with open(temp_mp3, "rb") as f:
                audio_bytes = f.read()

            duration = max(1.0, len(request.text) / (15.0 * max(0.5, request.speed)))

            return TTSResult(
                audio_bytes=audio_bytes,
                provider_request_id=f"edge_{uuid.uuid4().hex[:8]}",
                duration_seconds=round(duration, 2),
                format="mp3",
                metadata={"provider": "edge", "voice": voice_id}
            )
        except Exception as e:
            logger.error(f"Edge TTS error for voice {voice_id}: {e}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Edge TTS synthesis failed: {str(e)}"
            )
        finally:
            if os.path.exists(temp_mp3):
                try:
                    os.remove(temp_mp3)
                except Exception:
                    pass

    async def get_voices(self) -> List[Dict[str, Any]]:
        try:
            return await edge_tts.list_voices()
        except Exception:
            return []

    async def health_check(self) -> bool:
        return True

    def estimate_cost(self, request: TTSRequest) -> CostEstimate:
        return CostEstimate(
            currency="USD",
            estimated_amount=0.0,
            pricing_unit="characters"
        )
