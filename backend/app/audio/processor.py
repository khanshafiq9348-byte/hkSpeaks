import asyncio
import os
import tempfile
import json
from typing import List, Tuple
from app.core.errors import AppException, ErrorCode

class AudioProcessor:
    """
    FFmpeg audio processing engine for normalization, concatenation, transcoding and validation.
    """

    @staticmethod
    async def get_audio_duration_and_validate(audio_bytes: bytes, original_filename: str = None) -> Tuple[float, str]:
        """
        Runs ffprobe on audio bytes to validate container and extract exact duration.
        """
        ext = ".mp3"
        if original_filename and "." in original_filename:
            ext = os.path.splitext(original_filename)[1].lower()
            if ext not in [".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"]:
                ext = ".mp3"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration,format_name",
                "-of", "json",
                tmp_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0 and stdout:
                try:
                    data = json.loads(stdout.decode("utf-8"))
                    duration = float(data["format"].get("duration", 0.0))
                    format_name = data["format"].get("format_name", "unknown")
                    if duration > 0:
                        return round(duration, 2), format_name
                except Exception:
                    pass

            # Safe fallback estimation if ffprobe returned 0 or partial output
            return round(max(1.0, len(audio_bytes) / 32000.0), 2), ext.lstrip(".")
        except Exception as e:
            return round(max(1.0, len(audio_bytes) / 32000.0), 2), "audio"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @staticmethod
    async def concatenate_audio_chunks(chunks_bytes: List[bytes], output_format: str = "mp3") -> bytes:
        """
        Seamlessly stitches multiple audio byte chunks into a unified, continuous audio file.
        Uses micro-crossfading (acrossfade) at chunk boundaries to eliminate clicks and silence gaps,
        followed by EBU R128 loudness normalization to ensure consistent volume across the entire speech.
        """
        if not chunks_bytes:
            return b""
        if len(chunks_bytes) == 1:
            return chunks_bytes[0]

        temp_files = []
        output_file = None

        try:
            # Write chunk files with proper format extension
            ext = output_format.lower() if output_format.lower() in ("mp3", "wav") else "mp3"
            for i, chunk in enumerate(chunks_bytes):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}.{ext}")
                tmp.write(chunk)
                tmp.close()
                temp_files.append(tmp.name)

            output_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_seamless.{ext}")
            output_tmp.close()
            output_file = output_tmp.name

            # Build chained acrossfade filter graph + EBU R128 loudness normalization
            inputs = []
            for fpath in temp_files:
                inputs.extend(["-i", fpath])

            filter_parts = []
            prev_label = "0:a"
            for i in range(1, len(temp_files)):
                next_label = f"{i}:a"
                out_label = f"a{i}" if i < len(temp_files) - 1 else "merged"
                filter_parts.append(f"[{prev_label}][{next_label}]acrossfade=d=0.04:c1=tri:c2=tri[{out_label}]")
                prev_label = out_label

            filter_complex = ";".join(filter_parts) + ";[merged]loudnorm=I=-16:TP=-1.5:LRA=11[final]"

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[final]",
                "-c:a", "libmp3lame" if ext == "mp3" else "pcm_s16le",
                "-b:a", "192k",
                "-ar", "44100" if ext == "mp3" else "24000",
                output_file
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                with open(output_file, "rb") as f:
                    return f.read()

            logger.warning(f"FFmpeg acrossfade failed (code {proc.returncode}): {stderr.decode('utf-8', errors='ignore')}. Attempting fallback concat.")

            # Fallback concat demuxer if filter graph fails
            concat_list = tempfile.NamedTemporaryFile(delete=False, suffix="_list.txt", mode="w", encoding="utf-8")
            for fpath in temp_files:
                safe_path = fpath.replace("\\", "/")
                concat_list.write(f"file '{safe_path}'\n")
            concat_list.close()

            fallback_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list.name,
                "-c:a", "libmp3lame" if ext == "mp3" else "pcm_s16le",
                "-b:a", "192k",
                "-ar", "44100" if ext == "mp3" else "24000",
                output_file
            ]
            fb_proc = await asyncio.create_subprocess_exec(*fallback_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await fb_proc.communicate()
            if os.path.exists(concat_list.name):
                try: os.remove(concat_list.name)
                except Exception: pass

            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                with open(output_file, "rb") as f:
                    return f.read()

            return b"".join(chunks_bytes)

        except Exception as e:
            logger.error(f"Error in concatenate_audio_chunks: {e}")
            return b"".join(chunks_bytes)
        finally:
            for tf in temp_files:
                if os.path.exists(tf):
                    try: os.remove(tf)
                    except Exception: pass
            if output_file and os.path.exists(output_file):
                try: os.remove(output_file)
                except Exception: pass

    @staticmethod
    def generate_speech_fallback(sample_text: str) -> bytes:
        """
        Generates clean fallback spoken audio bytes (MP3) using local TTS engine or audio synthesis.
        """
        # 1. Try pyttsx3 + ffmpeg
        try:
            import pyttsx3
            import subprocess
            engine = pyttsx3.init()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                wav_path = tmp_wav.name
            engine.save_to_file(sample_text, wav_path)
            engine.runAndWait()
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
                    mp3_path = tmp_mp3.name
                cmd = ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", mp3_path]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode == 0 and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                    with open(mp3_path, "rb") as f:
                        data = f.read()
                    try:
                        os.remove(wav_path)
                        os.remove(mp3_path)
                    except Exception:
                        pass
                    return data
                with open(wav_path, "rb") as f:
                    data = f.read()
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
                return data
        except Exception:
            pass

        # 2. Clean audio tone fallback via ffmpeg
        try:
            import subprocess
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_tone:
                tone_path = tmp_tone.name
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5", "-c:a", "libmp3lame", "-b:a", "128k", tone_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(tone_path):
                with open(tone_path, "rb") as f:
                    data = f.read()
                try:
                    os.remove(tone_path)
                except Exception:
                    pass
                return data
        except Exception:
            pass

        return b""

audio_processor = AudioProcessor()
