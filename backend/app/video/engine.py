import os
import re
import json
import math
import uuid
import tempfile
import subprocess
import logging
from typing import List, Dict, Any, Optional
from PIL import Image

try:
    import speech_recognition as sr
except ImportError:
    sr = None

logger = logging.getLogger(__name__)

# Common English stop words to filter out for keyword matching
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers",
    "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've",
    "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while",
    "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

# Rich semantic concept clusters for documentary narratives
SEMANTIC_CLUSTERS = {
    "bag": ["bag", "leather", "pack", "briefcase", "satchel", "pouch", "strap", "buckle", "opening", "hands", "case"],
    "key": ["key", "brass", "lock", "unlock", "chest", "secret", "box", "wooden", "iron", "drawer"],
    "letter": ["letter", "paper", "scroll", "writing", "handwritten", "manuscript", "document", "parchment", "words", "note"],
    "reading": ["reading", "read", "man", "person", "study", "desk", "lamp", "light", "scholar", "looking", "eyes", "examining", "book"],
    "vintage": ["vintage", "antique", "old", "history", "ancient", "relic", "forgotten", "past", "heritage", "classic", "ruins", "artifact"],
    "mystery": ["mystery", "mysteries", "secret", "secrets", "hidden", "shadow", "dark", "unknown", "discover", "reveal", "enigma"],
    "desk": ["desk", "table", "wooden", "wood", "room", "interior", "workspace", "surface"],
    "nature": ["nature", "mountain", "mountains", "river", "lake", "forest", "tree", "trees", "ocean", "sea", "sky", "horizon", "landscape", "wild", "valley", "earth"],
    "architecture": ["building", "castle", "palace", "temple", "ruins", "tower", "bridge", "city", "street", "wall", "stone", "monument", "pyramid", "structure"],
    "journey": ["journey", "travel", "road", "path", "voyage", "expedition", "walk", "destination", "adventure", "explore", "route"],
    "science": ["science", "cosmos", "stars", "space", "astronomy", "laboratory", "discovery", "experiment", "universe", "planets", "tech"],
    "war": ["war", "battle", "soldier", "soldiers", "conflict", "sword", "shield", "army", "struggle", "fight", "victory", "conquest"],
    "people": ["people", "crowd", "man", "woman", "child", "society", "face", "portrait", "leader", "eyes", "gathering", "human", "figure"],
    "water": ["water", "sea", "ocean", "wave", "lake", "river", "rain", "storm", "ice", "tide"],
    "time": ["time", "clock", "hours", "century", "years", "ancient", "future", "era", "epoch", "memory", "memories"]
}

class DocumentaryEngine:
    """
    Core timeline and auto-editing engine:
    Voiceover -> Analysis & Transcription -> Sentences with Timestamps -> Intelligent Image Pool Allocation -> Synchronized Timeline -> FFmpeg
    """

    @staticmethod
    def probe_audio(audio_path: str) -> Dict[str, Any]:
        """
        Probes audio file using ffprobe to obtain exact duration, channels, sample rate.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size:stream=sample_rate,channels,codec_name",
            "-of", "json",
            audio_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(res.stdout)
            fmt = data.get("format", {})
            duration = float(fmt.get("duration", 0.0))
            streams = data.get("streams", [])
            sample_rate = 44100
            channels = 2
            if streams:
                sample_rate = int(streams[0].get("sample_rate", 44100))
                channels = int(streams[0].get("channels", 2))
            return {
                "duration": round(duration, 3),
                "sample_rate": sample_rate,
                "channels": channels,
                "file_size": int(fmt.get("size", os.path.getsize(audio_path)))
            }
        except Exception as e:
            logger.warning(f"ffprobe failed, attempting fallback duration estimation: {e}")
            return {
                "duration": 10.0,
                "sample_rate": 44100,
                "channels": 2,
                "file_size": os.path.getsize(audio_path)
            }

    @classmethod
    def transcribe_and_segment_voiceover(
        cls,
        audio_path: str,
        total_duration: float
    ) -> List[Dict[str, Any]]:
        """
        1. Analyzes speech cadence, pause intervals, and sentence timestamps.
        2. Performs automatic speech-to-text transcription for each sentence segment.
        3. Returns timestamped sentences strictly covering [0.0, total_duration].
        """
        if total_duration <= 0.0:
            total_duration = 10.0

        # Step A: Convert audio to standard 16kHz mono WAV for processing
        temp_dir = tempfile.gettempdir()
        temp_wav = os.path.join(temp_dir, f"vo_proc_{uuid.uuid4().hex[:8]}.wav")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000", "-ac", "1",
                temp_wav
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            logger.warning(f"Audio normalization failed: {e}")
            temp_wav = audio_path

        # Step B: Detect natural pause / sentence boundaries
        silence_cuts = []
        try:
            cmd = [
                "ffmpeg", "-i", temp_wav,
                "-af", "silencedetect=noise=-28dB:d=0.25",
                "-f", "null", "-"
            ]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
            for line in res.stderr.splitlines():
                if "silence_end:" in line:
                    match = re.search(r"silence_end:\s*([0-9.]+)", line)
                    if match:
                        val = float(match.group(1))
                        if 1.5 < val < total_duration - 1.2:
                            silence_cuts.append(round(val, 2))
        except Exception as e:
            logger.warning(f"Silence detection warning: {e}")

        # Assemble boundaries ensuring each scene is between ~2.5s and 6.5s
        boundaries = [0.0]
        if silence_cuts:
            last_b = 0.0
            for cut in silence_cuts:
                if (cut - last_b) >= 2.5:
                    boundaries.append(cut)
                    last_b = cut
        else:
            # Natural cadence: divide into ~3.5s to 4.5s sentence scenes
            target_dur = 4.0
            num_scenes = max(1, math.ceil(total_duration / target_dur))
            step = total_duration / num_scenes
            curr = 0.0
            for i in range(num_scenes - 1):
                curr += step
                boundaries.append(round(curr, 2))

        if boundaries[-1] < total_duration:
            boundaries.append(round(total_duration, 2))
        else:
            boundaries[-1] = round(total_duration, 2)

        # Step C: Speech-to-Text Transcription for each boundary interval
        recognizer = sr.Recognizer() if sr else None
        full_audio_transcription = ""

        # Attempt full speech recognition first to capture overall context
        if recognizer and os.path.exists(temp_wav):
            try:
                with sr.AudioFile(temp_wav) as source:
                    full_audio = recognizer.record(source)
                    full_audio_transcription = recognizer.recognize_google(full_audio)
                    logger.info(f"Full voiceover transcribed: '{full_audio_transcription}'")
            except Exception as e:
                logger.info(f"Full voiceover STT note: {e}")

        full_words = full_audio_transcription.split() if full_audio_transcription else []

        segments = []
        num_intervals = len(boundaries) - 1

        for i in range(num_intervals):
            start = boundaries[i]
            end = boundaries[i + 1]
            dur = round(end - start, 2)
            if dur <= 0.2:
                continue

            sentence_text = ""

            # Attempt segment-specific transcription
            if recognizer and os.path.exists(temp_wav):
                try:
                    with sr.AudioFile(temp_wav) as source:
                        seg_audio = recognizer.record(source, offset=start, duration=dur)
                        sentence_text = recognizer.recognize_google(seg_audio).strip()
                except Exception:
                    pass

            # Fallback 1: Word partition from full transcription if segment-specific was silent
            if not sentence_text and full_words:
                w_start = int((start / total_duration) * len(full_words))
                w_end = int((end / total_duration) * len(full_words))
                if w_start < len(full_words):
                    chunk = full_words[w_start:max(w_start + 1, w_end)]
                    if chunk:
                        sentence_text = " ".join(chunk)

            # Fallback 2: Clean thematic sentence if STT was unavailable
            if not sentence_text:
                sentence_text = f"Documentary narration segment {i + 1} ({start}s - {end}s)"
            else:
                sentence_text = sentence_text[0].upper() + sentence_text[1:]
                if not sentence_text.endswith((".", "!", "?")):
                    sentence_text += "."

            # Extract content keywords for semantic matching
            clean_words = re.findall(r"[a-zA-Z]{3,}", sentence_text.lower())
            keywords = [w for w in clean_words if w not in STOP_WORDS]

            title = f"Scene {i + 1}"
            if keywords:
                sample_kws = [k.capitalize() for k in keywords[:2]]
                title = f"Scene {i + 1}: {' & '.join(sample_kws)}"

            segments.append({
                "segment_index": i,
                "start_time": start,
                "end_time": end,
                "duration": dur,
                "title": title,
                "text": sentence_text,
                "keywords": keywords
            })

        # Cleanup temp wav
        if os.path.exists(temp_wav) and temp_wav != audio_path:
            try:
                os.remove(temp_wav)
            except Exception:
                pass

        if not segments:
            segments.append({
                "segment_index": 0,
                "start_time": 0.0,
                "end_time": round(total_duration, 2),
                "duration": round(total_duration, 2),
                "title": "Scene 1",
                "text": full_audio_transcription or "Master documentary scene narration.",
                "keywords": ["documentary", "history"]
            })

        return segments

    @classmethod
    def detect_speech_segments(cls, audio_path: str, total_duration: float) -> List[Dict[str, Any]]:
        """Backwards compatible wrapper invoking transcribe_and_segment_voiceover."""
        return cls.transcribe_and_segment_voiceover(audio_path, total_duration)

    @staticmethod
    def tokenize_text(text: str) -> List[str]:
        """Splits camelCase, snake_case, and non-alphanumerics into lower-case non-stopword tokens."""
        s = re.sub(r"([a-z])([A-Z])", r" ", text)
        tokens = [t.lower() for t in re.findall(r"[a-zA-Z]{3,}", s)]
        return [t for t in tokens if t not in STOP_WORDS]

    @classmethod
    def analyze_image(cls, image_path: str, filename: str) -> Dict[str, Any]:
        """
        Analyzes visual content, aspect ratio, resolution, dominant colors, and semantic tags.
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                aspect = round(width / max(1, height), 3)

                img_small = img.convert("RGB").resize((32, 32))
                colors = img_small.getcolors(maxcolors=1024)
                dominant = []
                if colors:
                    colors.sort(key=lambda x: x[0], reverse=True)
                    for count, col in colors[:3]:
                        dominant.append(f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}")

                # Extract rich keywords from filename
                base_name = os.path.splitext(filename)[0]
                clean_tags = cls.tokenize_text(base_name)
                tags = list(dict.fromkeys(clean_tags))

                # Color tone analysis
                if colors:
                    total_px = sum(c[0] for c in colors)
                    avg_r = sum(c[0] * c[1][0] for c in colors) / total_px
                    avg_g = sum(c[0] * c[1][1] for c in colors) / total_px
                    avg_b = sum(c[0] * c[1][2] for c in colors) / total_px
                    lum = (0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b)

                    if lum < 70:
                        tags.extend(["dark", "shadow", "mystery"])
                    elif lum > 175:
                        tags.extend(["bright", "light", "day"])

                    if avg_r > 1.25 * avg_b and avg_r > 1.15 * avg_g:
                        tags.extend(["warm", "vintage", "ancient"])
                    elif avg_b > 1.2 * avg_r:
                        tags.extend(["cool", "night", "water"])
                    elif avg_g > 1.15 * avg_r and avg_g > 1.15 * avg_b:
                        tags.extend(["nature", "forest"])

                # Aspect ratio tags
                if aspect > 1.3:
                    tags.append("landscape")
                elif aspect < 0.8:
                    tags.append("portrait")
                else:
                    tags.append("square")

                tag_list = list(dict.fromkeys([t.lower() for t in tags if t.lower() not in STOP_WORDS]))

                return {
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect,
                    "dominant_colors": dominant or ["#1e293b", "#0f172a"],
                    "tags": tag_list,
                    "description": f"Visual asset {filename} ({', '.join(tag_list[:4])})"
                }
        except Exception as e:
            logger.error(f"Image analysis failed for {image_path}: {e}")
            base_name = os.path.splitext(filename)[0]
            clean_tags = cls.tokenize_text(base_name)
            return {
                "width": 1920,
                "height": 1080,
                "aspect_ratio": 1.778,
                "dominant_colors": ["#1e293b", "#0f172a"],
                "tags": clean_tags or ["documentary", "visual"],
                "description": f"Uploaded asset {filename}"
            }

    @classmethod
    def calculate_relevance_score(
        cls,
        sentence_keywords: List[str],
        sentence_text: str,
        image_asset: Dict[str, Any],
        is_previous_selection: bool = False
    ) -> float:
        """
        Computes semantic relevance score between a spoken sentence and an uploaded image.
        Uses direct filename tokens, semantic concepts, and visual metadata.
        """
        score = 0.0
        filename = image_asset.get("filename", "")
        fn_tokens = set(cls.tokenize_text(os.path.splitext(filename)[0]))
        tags = set(t.lower() for t in image_asset.get("tags", [])) - STOP_WORDS
        all_asset_tokens = fn_tokens | tags

        sentence_tokens = set(cls.tokenize_text(sentence_text)) | set(k.lower() for k in sentence_keywords)

        # 1. Direct filename word match (+50 points per matching word)
        exact_matches = sentence_tokens & all_asset_tokens
        score += len(exact_matches) * 50.0

        # 2. Substring / partial match (+30 points)
        for st in sentence_tokens:
            for at in all_asset_tokens:
                if len(st) >= 4 and len(at) >= 4 and st != at:
                    if st in at or at in st:
                        score += 30.0

        # 3. Semantic Cluster match (+20 points per shared cluster)
        sentence_lower = sentence_text.lower()
        for cluster_name, synonyms in SEMANTIC_CLUSTERS.items():
            s_has = any(s in sentence_lower for s in synonyms)
            a_has = any(s in all_asset_tokens for s in synonyms) or (cluster_name in all_asset_tokens)
            if s_has and a_has:
                score += 20.0

        # 4. Aspect / visual mood fit (+10 points)
        if ("landscape" in sentence_tokens or "journey" in sentence_tokens) and "landscape" in tags:
            score += 10.0
        if ("person" in sentence_tokens or "who" in sentence_tokens) and "portrait" in tags:
            score += 10.0

        # 5. Deterministic tie breaker based on scene & asset id (between 0.01 and 0.99)
        asset_id = str(image_asset.get("id", filename))
        h = abs(hash(f"{sentence_text[:15]}_{asset_id}")) % 100
        score += (h / 100.0)

        # 6. Recency penalty if is_previous_selection
        if is_previous_selection:
            score -= 25.0

        return score

    @classmethod
    def segment_audio_for_sequential_images(
        cls,
        audio_path: str,
        total_duration: float,
        num_images: int,
        script_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyzes voiceover audio sentence-by-sentence using silence detection to determine
        exact timestamps for each sequential uploaded image:
        - Image 1 -> Sentence 1 (0:00 - cut 1)
        - Image 2 -> Sentence 2 (cut 1 - cut 2)
        - Image 3 -> Sentence 3 (cut 2 - cut 3)
        ...
        - Image N -> Sentence N (cut N-1 - total_duration)

        Strictly maintains exact sequential order, never reorders images.
        """
        if total_duration <= 0.0:
            total_duration = 10.0

        N = max(1, num_images)
        if N == 1:
            return [{
                "segment_index": 0,
                "start_time": 0.0,
                "end_time": round(total_duration, 2),
                "duration": round(total_duration, 2),
                "title": "Scene 1",
                "text": script_text.strip() if script_text else f"Scene 1 (0:00 - {round(total_duration, 1)}s)",
                "keywords": ["documentary"]
            }]

        # 1. Fast ffmpeg silence detection to find natural sentence pauses
        silence_cuts = []
        try:
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-af", "silencedetect=noise=-30dB:d=0.20",
                "-f", "null", "-"
            ]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
            cur_start = None
            for line in res.stderr.splitlines():
                if "silence_start:" in line:
                    m = re.search(r"silence_start:\s*([0-9.]+)", line)
                    if m:
                        cur_start = float(m.group(1))
                elif "silence_end:" in line:
                    m = re.search(r"silence_end:\s*([0-9.]+)", line)
                    if m:
                        end_val = float(m.group(1))
                        mid = (cur_start + end_val) / 2.0 if cur_start is not None else end_val
                        if 0.8 < mid < total_duration - 0.8:
                            silence_cuts.append(round(mid, 2))
                        cur_start = None
        except Exception as e:
            logger.warning(f"Silence detection warning: {e}")

        # 2. Derive N-1 boundary cut points aligned with speech pauses
        min_dur = max(1.0, min(2.5, total_duration / (N * 1.5)))
        boundaries = [0.0]

        for k in range(1, N):
            rem_scenes = N - k + 1
            rem_time = total_duration - boundaries[-1]
            nominal_step = rem_time / rem_scenes
            target = boundaries[-1] + nominal_step

            earliest = boundaries[-1] + min_dur
            latest = total_duration - (N - k) * min_dur

            chosen_cut = None
            if latest > earliest:
                candidates = [c for c in silence_cuts if earliest <= c <= latest]
                if candidates:
                    candidates.sort(key=lambda c: abs(c - target))
                    chosen_cut = candidates[0]

            if chosen_cut is None:
                chosen_cut = round(target, 2)
            else:
                chosen_cut = round(chosen_cut, 2)

            boundaries.append(chosen_cut)

        boundaries.append(round(total_duration, 2))

        # 3. Parse script sentences if provided
        script_sentences = []
        if script_text:
            raw_lines = [l.strip() for l in re.split(r'[\r\n]+|(?<=[.!?])\s+', script_text) if l.strip()]
            script_sentences = raw_lines

        segments = []
        for i in range(N):
            start = boundaries[i]
            end = boundaries[i + 1]
            dur = round(end - start, 2)

            text = ""
            if i < len(script_sentences):
                text = script_sentences[i]
            elif script_sentences:
                idx_map = min(int(i * len(script_sentences) / N), len(script_sentences) - 1)
                text = script_sentences[idx_map]
            else:
                text = f"Sentence {i + 1} ({round(start, 1)}s - {round(end, 1)}s)"

            title = f"Scene {i + 1}"
            segments.append({
                "segment_index": i,
                "start_time": start,
                "end_time": end,
                "duration": dur,
                "title": title,
                "text": text,
                "keywords": []
            })

        return segments

    @classmethod
    def allocate_images_to_scenes(
        cls,
        speech_segments: List[Dict[str, Any]],
        image_assets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Allocates uploaded images in EXACT sequential upload order:
        Image 1 -> Scene 1
        Image 2 -> Scene 2
        Image 3 -> Scene 3
        Image 4 -> Scene 4
        ...etc.

        CRITICAL: Never reorders images based on AI relevance or content tags.
        """
        M = len(speech_segments)
        N = len(image_assets)
        if N == 0:
            raise ValueError("At least one visual image asset is required to build timeline.")

        allocated = []
        for i in range(M):
            if i < N:
                allocated.append(image_assets[i])
            else:
                allocated.append(image_assets[min(int(i * N / M), N - 1)])
        return allocated

    @classmethod
    def generate_timeline(
        cls,
        total_duration: float,
        speech_segments: List[Dict[str, Any]],
        image_assets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Automatically builds the synchronized multi-track visual timeline:
        - Image duration strictly matches the voiceover sentence timestamps!
        - When one sentence ends, the next relevant image starts automatically.
        - Uses the full available image pool intelligently based on narration relevance.
        - Only reuses an image when there are genuinely more narration segments than images.
        - Cinematic Ken Burns motion tailored to scene narrative.
        """
        if not image_assets:
            raise ValueError("At least one visual image asset is required to build timeline.")

        motion_styles = ["zoom_in", "pan_right", "zoom_out", "pan_left", "ken_burns"]
        transitions_pool = ["crossfade", "fade_black", "dissolve", "crossfade"]

        # Intelligently distribute full pool of images across speech segments
        selected_assets = cls.allocate_images_to_scenes(speech_segments, image_assets)

        scenes = []
        clips = []
        transitions = []

        for idx, seg in enumerate(speech_segments):
            sentence_text = seg.get("text", "")
            best_asset = selected_assets[idx]

            scene_id = f"scene_{idx + 1}"
            clip_id = f"clip_{idx + 1}"

            clip_dur = seg["duration"]
            start_t = seg["start_time"]
            end_t = seg["end_time"]

            # Dynamic motion style based on sentence feel
            motion = motion_styles[idx % len(motion_styles)]
            s_lower = sentence_text.lower()
            if "unlock" in s_lower or "secret" in s_lower or "key" in s_lower:
                motion = "zoom_in"
            elif "memories" in s_lower or "past" in s_lower or "history" in s_lower:
                motion = "ken_burns"
            elif "read" in s_lower or "letter" in s_lower or "manuscript" in s_lower:
                motion = "pan_right"
            elif "mountain" in s_lower or "horizon" in s_lower or "sky" in s_lower:
                motion = "zoom_out"

            # Scene record
            scene = {
                "id": scene_id,
                "scene_index": idx,
                "title": seg.get("title", f"Scene {idx + 1}"),
                "narrative_text": sentence_text,
                "start_time": start_t,
                "end_time": end_t,
                "duration": clip_dur,
                "primary_asset_id": best_asset["id"],
                "asset": best_asset
            }
            scenes.append(scene)

            # Timeline clip record
            clip = {
                "id": clip_id,
                "scene_id": scene_id,
                "asset_id": best_asset["id"],
                "track_index": 0,
                "clip_index": idx,
                "start_time": start_t,
                "end_time": end_t,
                "duration": clip_dur,
                "motion_type": motion,
                "scale_factor": 1.15,
                "framing": "cover",
                "asset": best_asset
            }
            clips.append(clip)

            # Transition between clips
            if idx > 0:
                trans_type = transitions_pool[(idx - 1) % len(transitions_pool)]
                trans_dur = 0.4 if clip_dur > 2.0 else 0.2
                transitions.append({
                    "id": f"trans_{idx}",
                    "from_clip_id": clips[idx - 1]["id"],
                    "to_clip_id": clip_id,
                    "transition_type": trans_type,
                    "duration": trans_dur,
                    "offset_time": start_t
                })

        return {
            "total_duration": total_duration,
            "scenes": scenes,
            "timeline_clips": clips,
            "transitions": transitions
        }

documentary_engine = DocumentaryEngine()
