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

# Dedicated voice pools for custom / cloned voices (distinct from default voices)
CUSTOM_FEMALE_VOICES = [
    "en-GB-LibbyNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-AnaNeural",
    "en-GB-SoniaNeural",
    "en-GB-MaisieNeural",
]

CUSTOM_MALE_VOICES = [
    "en-US-BrianMultilingualNeural",
    "en-US-AndrewMultilingualNeural",
    "en-US-SteffanNeural",
    "en-US-RogerNeural",
    "en-GB-ThomasNeural",
]

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
                if candidate and candidate in valid_voices and candidate not in ("en-US-GuyNeural", "en-US-JennyNeural"):
                    return candidate

            # Deterministic mapping from request.voice_id to guaranteed distinct neural model
            import hashlib
            h = int(hashlib.md5((request.voice_id or "default-clone").encode("utf-8")).hexdigest(), 16)
            if (request.gender or "").lower() == "female":
                return CUSTOM_FEMALE_VOICES[h % len(CUSTOM_FEMALE_VOICES)]
            return CUSTOM_MALE_VOICES[h % len(CUSTOM_MALE_VOICES)]

        # 2. Direct match with valid Edge shortnames
        p_id = request.provider_voice_id or ""
        if p_id in valid_voices:
            return p_id

        if request.model and request.model in valid_voices:
            return request.model

        # 3. Known showcase aliases
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

        # Never silently replace a specified voice with an arbitrary fallback
        if p_id:
            logger.error(f"[Edge TTS] Explicit voice '{p_id}' is not in valid voices catalog.")
            raise AppException(
                status_code=400,
                error_code=ErrorCode.VOICE_NOT_FOUND,
                message=f"Voice '{p_id}' is not an active verified voice."
            )

        if request.model:
            logger.error(f"[Edge TTS] Explicit voice model '{request.model}' is not in valid voices catalog.")
            raise AppException(
                status_code=400,
                error_code=ErrorCode.VOICE_NOT_FOUND,
                message=f"Voice model '{request.model}' is not an active verified voice."
            )

        # 4. Match by exact locale and gender (only if no specific voice was requested)
        target_gender = "Male" if (request.gender or "").lower() == "male" else "Female"
        if request.locale:
            matching_locale = [
                sn for sn, v in valid_voices.items()
                if v.get("Locale", "").lower() == request.locale.lower()
                and v.get("Gender", "").lower() == target_gender.lower()
            ]
            if matching_locale:
                seed = request.voice_id or "default"
                idx = abs(hash(seed)) % len(matching_locale)
                return matching_locale[idx]

        # 5. Match by language and gender
        lang = (request.language or "en").lower().split("-")[0]
        matching_lang = [
            sn for sn, v in valid_voices.items()
            if v.get("Locale", "").lower().startswith(f"{lang}-")
            and v.get("Gender", "").lower() == target_gender.lower()
        ]
        if matching_lang:
            seed = request.voice_id or "default"
            idx = abs(hash(seed)) % len(matching_lang)
            return matching_lang[idx]

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

        rate_pct = int(round((max(0.5, min(request.speed, 2.0)) - 1.0) * 100))
        rate_str = f"{rate_pct:+d}%"

        expr = getattr(request, "expressiveness", 0.7)
        if expr is None:
            expr = 0.7
        pitch_dynamic = (float(expr) - 0.5) * 4.0
        pitch_hz = int(round(max(-10.0, min(request.pitch, 10.0)) * 6.0 + pitch_dynamic))
        pitch_str = f"{pitch_hz:+d}Hz"

        vol_val = request.volume if request.volume is not None else 0.0
        if vol_val > 25.0:  # legacy percentage scale (e.g. 100%)
            vol_pct = int(round(max(-90.0, min(vol_val - 100.0, 200.0))))
        else:  # dB scale (-20dB to +20dB, where 0dB = 1.0 gain = 0%)
            linear_gain = 10.0 ** (max(-20.0, min(vol_val, 20.0)) / 20.0)
            vol_pct = int(round((linear_gain - 1.0) * 100.0))
            vol_pct = max(-90, min(vol_pct, 200))
        vol_str = f"{vol_pct:+d}%"

        logger.info(
            f"[EdgeTTS Neural Synthesis] Voice='{voice_id}', Speed={request.speed}x (rate='{rate_str}'), "
            f"Pitch={request.pitch} (pitch='{pitch_str}'), Volume={request.volume}dB/pct (vol='{vol_str}'), "
            f"Expressiveness={expr}, Diversity={getattr(request, 'diversity', 0.7)}"
        )

        temp_dir = tempfile.gettempdir()
        temp_mp3 = os.path.join(temp_dir, f"edge_out_{uuid.uuid4().hex[:8]}.mp3")
        try:
            communicate = edge_tts.Communicate(
                text=request.text,
                voice=voice_id,
                rate=rate_str,
                pitch=pitch_str,
                volume=vol_str
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
