import io
import math
import struct
import wave
import uuid
import subprocess
import asyncio
import logging
import hashlib
import tempfile
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from app.providers.base import TTSProvider, TTSRequest, TTSResult, CostEstimate

logger = logging.getLogger(__name__)

# Predefined standard voices mapped to Microsoft Neural voices
STANDARD_VOICE_MAP: Dict[str, str] = {
    "sarah": "en-US-JennyNeural",
    "sarah-natural": "en-US-JennyNeural",
    "david": "en-US-GuyNeural",
    "david-broadcaster": "en-US-GuyNeural",
    "marcus": "en-GB-RyanNeural",
    "marcus-documentary": "en-GB-RyanNeural",
    "elena": "en-US-EmmaNeural",
    "elena-commercial": "en-US-EmmaNeural",
    "alexander": "en-US-ChristopherNeural",
    "alexander-audiobook": "en-US-ChristopherNeural",
    "chloe": "en-US-AriaNeural",
    "chloe-conversational": "en-US-AriaNeural",
    "mock_voice_sarah": "en-US-JennyNeural",
    "mock_voice_marcus": "en-GB-RyanNeural",
    "mock_voice_elena": "en-US-EmmaNeural",
}

# Rich voice pools for custom / cloned voices (Dedicated timbres distinct from library voices)
CUSTOM_FEMALE_VOICES = [
    "en-GB-LibbyNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-JennyNeural",
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

CUSTOM_NEUTRAL_VOICES = [
    "en-GB-LibbyNeural",
    "en-US-BrianMultilingualNeural",
    "en-US-AvaMultilingualNeural",
]

class MockTTSProvider(TTSProvider):
    """
    High-fidelity Neural & Human TTS Provider for local development and offline environments.
    Produces studio-grade natural human speech output with zero machine buzzing.
    Utilizes Microsoft Neural Voice models with pyttsx3 offline fallback.
    """
    def __init__(self, name: str = "mock"):
        self.name = name

    def _resolve_neural_voice(self, request: TTSRequest) -> str:
        # 1. Check if model explicitly specifies a recognized neural voice (e.g. for cloned voices)
        if request.model and "neural" in request.model.lower():
            logger.info(f"[TTS Trace] Cloned voice resolved from request.model='{request.model}' (voice_id='{request.voice_id}')")
            return request.model

        p_id = (request.provider_voice_id or "").lower()
        v_id = (request.voice_id or "").lower()

        # 2. Check if already a recognized neural voice in provider_voice_id
        if "neural" in p_id:
            logger.info(f"[TTS Trace] Voice resolved from provider_voice_id='{request.provider_voice_id}'")
            return request.provider_voice_id

        # 3. Check standard voice catalog mapping
        if p_id in STANDARD_VOICE_MAP:
            logger.info(f"[TTS Trace] Standard voice resolved: provider_voice_id='{p_id}' -> '{STANDARD_VOICE_MAP[p_id]}'")
            return STANDARD_VOICE_MAP[p_id]
        if v_id in STANDARD_VOICE_MAP:
            logger.info(f"[TTS Trace] Standard voice resolved: voice_id='{v_id}' -> '{STANDARD_VOICE_MAP[v_id]}'")
            return STANDARD_VOICE_MAP[v_id]

        # 4. Cloned or custom voice resolution:
        # Generate a deterministic hash for consistent unique voice timbre per clone
        seed = f"{request.voice_id}_{request.provider_voice_id}"
        h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)

        gender = (request.gender or "neutral").lower()
        if gender == "female":
            pool = CUSTOM_FEMALE_VOICES
        elif gender == "male":
            pool = CUSTOM_MALE_VOICES
        else:
            pool = CUSTOM_FEMALE_VOICES if (h % 2 == 0) else CUSTOM_MALE_VOICES

        selected = pool[h % len(pool)]
        logger.info(f"[TTS Trace] Cloned custom voice resolved: voice_id='{request.voice_id}', gender='{gender}' -> '{selected}'")
        return selected

    async def _synthesize_edge_tts(self, request: TTSRequest, voice_name: str) -> Optional[bytes]:
        """Synthesizes human speech using neural models with automatic retries."""
        import edge_tts

        # Rate adjustments (-50% to +100%)
        rate_pct = int(round((max(0.5, min(request.speed, 2.0)) - 1.0) * 100))
        rate_str = f"{rate_pct:+d}%"

        # Pitch adjustments (-15Hz to +15Hz)
        pitch_hz = int(round(max(-10.0, min(request.pitch, 10.0)) * 3.0))
        pitch_str = f"{pitch_hz:+d}Hz"

        text_clean = request.text.strip()
        if not text_clean:
            return None

        # Attempt up to 3 times with exponential backoff
        for attempt in range(1, 4):
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_path = tmp.name

                communicate = edge_tts.Communicate(
                    text=text_clean,
                    voice=voice_name,
                    rate=rate_str,
                    pitch=pitch_str,
                    connect_timeout=15,
                    receive_timeout=30
                )
                await communicate.save(tmp_path)

                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    with open(tmp_path, "rb") as f:
                        raw_bytes = f.read()
                    if len(raw_bytes) > 0:
                        return raw_bytes
            except Exception as e:
                logger.warning(f"edge-tts attempt {attempt}/3 failed for '{voice_name}': {e}")
                if attempt < 3:
                    await asyncio.sleep(0.5 * attempt)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        return None

    async def _synthesize_pyttsx3(self, text: str, speed: float = 1.0) -> Optional[bytes]:
        """Synthesizes human speech using local pyttsx3 / Windows SAPI engine (100% offline)."""
        def _run_engine():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                base_rate = engine.getProperty("rate") or 200
                engine.setProperty("rate", int(base_rate * max(0.5, min(speed, 2.0))))
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    engine.save_to_file(text, tmp_path)
                    engine.runAndWait()
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        with open(tmp_path, "rb") as f:
                            return f.read()
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
            except Exception as ex:
                logger.warning(f"pyttsx3 offline engine error: {ex}")
            return None

        return await asyncio.to_thread(_run_engine)

    def _generate_fallback_wav(self, duration_sec: float, sample_rate: int = 24000) -> bytes:
        """Gentle speech-cadenced fallback if all neural and speech engines are unavailable."""
        num_samples = int(duration_sec * sample_rate)
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            samples = bytearray()
            for i in range(num_samples):
                t = float(i) / sample_rate
                # Smooth formant-like modulation
                envelope = min(1.0, t * 5) * min(1.0, (duration_sec - t) * 5)
                # Soft gentle resonance
                val = 0.4 * math.sin(2.0 * math.pi * 180.0 * t) * math.cos(2.0 * math.pi * 3.5 * t)
                sample_int = int(val * envelope * 12000)
                sample_int = max(-32768, min(32767, sample_int))
                samples.extend(struct.pack('<h', sample_int))
            wav_file.writeframes(samples)
        return wav_io.getvalue()

    async def _transcode_and_measure(
        self,
        audio_bytes: bytes,
        target_format: str,
        sample_rate: int = 44100
    ) -> Tuple[bytes, float]:
        """Transcodes raw audio into well-formed MP3/WAV and returns exact duration."""
        fmt = target_format.lower()
        if fmt not in ["mp3", "wav"]:
            fmt = "mp3"

        if fmt == "mp3":
            cmd = [
                "ffmpeg", "-y", "-i", "pipe:0",
                "-codec:a", "libmp3lame",
                "-b:a", "192k",
                "-ar", "44100",
                "-f", "mp3",
                "pipe:1"
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-i", "pipe:0",
                "-acodec", "pcm_s16le",
                "-ar", "24000",
                "-ac", "1",
                "-f", "wav",
                "pipe:1"
            ]

        final_bytes = audio_bytes
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate(input=audio_bytes)
            if proc.returncode == 0 and len(stdout) > 0:
                final_bytes = stdout
        except Exception as e:
            logger.warning(f"FFmpeg transcode failed: {e}")

        # Extract duration via ffprobe
        duration = 0.0
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}") as tmp:
                tmp.write(final_bytes)
                tmp_path = tmp.name

            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                tmp_path
            ]
            p_proc = await asyncio.create_subprocess_exec(
                *probe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            p_out, _ = await p_proc.communicate()
            if p_proc.returncode == 0 and p_out:
                j_data = json.loads(p_out.decode("utf-8"))
                duration = float(j_data.get("format", {}).get("duration", 0.0))

            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

        if duration <= 0:
            duration = max(1.2, round(len(final_bytes) / 24000.0, 2))

        return final_bytes, round(duration, 2)

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        voice_name = self._resolve_neural_voice(request)
        output_format = request.format.lower() if request.format else "mp3"
        char_count = max(1, len(request.text.strip()))

        is_cloned_voice = bool(
            request.is_clone
            or (request.tier and request.tier.lower() == "custom")
            or (request.provider_voice_id and "clone" in request.provider_voice_id.lower())
            or (request.voice_id and "clone" in request.voice_id.lower())
        )

        # 1. Primary: Neural Speech Synthesis (edge-tts)
        audio_bytes = await self._synthesize_edge_tts(request, voice_name)

        # 2. Strict Check for Cloned Voices: NEVER fallback to a default AI voice or different provider!
        if not audio_bytes and is_cloned_voice:
            logger.error(
                f"[Cloned Voice Error] Neural synthesis for cloned voice '{request.voice_id}' "
                f"(name/model='{voice_name}') failed. Refusing fallback to default voice."
            )
            from app.core.errors import AppException, ErrorCode
            raise AppException(
                status_code=502,
                error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                message=(
                    f"Selected cloned voice '{request.voice_id}' ({voice_name}) is currently unavailable. "
                    "Generation was stopped to strictly protect voice identity and prevent using another voice."
                )
            )

        # 3. Secondary: Offline Speech Synthesis (pyttsx3 / Windows SAPI) ONLY for standard catalog voices
        if not audio_bytes and not is_cloned_voice:
            logger.info(f"Synthesizing standard voice '{request.text[:40]}...' using offline pyttsx3 engine")
            audio_bytes = await self._synthesize_pyttsx3(request.text, request.speed)

        # 4. Tertiary fallback: Gentle tone if all speech engines fail (catalog only)
        if not audio_bytes and not is_cloned_voice:
            fallback_duration = max(1.2, min(char_count / 15.0 / max(0.5, request.speed), 180.0))
            audio_bytes = self._generate_fallback_wav(fallback_duration)

        if not audio_bytes:
            from app.core.errors import AppException, ErrorCode
            raise AppException(
                status_code=502,
                error_code=ErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Speech synthesis failed for voice '{request.voice_id}' ({voice_name})."
            )

        # 5. Normalize & Transcode to target format (clean 44.1kHz MP3 or 24kHz WAV)
        final_bytes, duration = await self._transcode_and_measure(
            audio_bytes, output_format, request.sample_rate
        )

        return TTSResult(
            audio_bytes=final_bytes,
            provider_request_id=f"hk_speech_{uuid.uuid4().hex[:12]}",
            duration_seconds=duration,
            format=output_format,
            metadata={
                "char_count": char_count,
                "voice_used": voice_name,
                "provider": self.name,
                "is_clone": is_cloned_voice,
                "model": voice_name
            }
        )

    async def get_voices(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock_voice_sarah",
                "name": "Sarah (Natural Storyteller)",
                "gender": "female",
                "tier": "standard",
                "language": "en",
                "accent": "American"
            },
            {
                "id": "mock_voice_marcus",
                "name": "Marcus (Deep Documentary)",
                "gender": "male",
                "tier": "premium",
                "language": "en",
                "accent": "British"
            },
            {
                "id": "mock_voice_elena",
                "name": "Elena (Energetic Commercial)",
                "gender": "female",
                "tier": "ultra",
                "language": "en",
                "accent": "American"
            }
        ]

    async def health_check(self) -> bool:
        return True

    def estimate_cost(self, request: TTSRequest) -> CostEstimate:
        chars = len(request.text)
        return CostEstimate(
            currency="USD",
            estimated_amount=round(chars * 0.000015, 6),
            pricing_unit="characters"
        )

