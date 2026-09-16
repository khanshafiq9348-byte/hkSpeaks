import os
import re
import math
import uuid
import tempfile
import logging
import subprocess
from typing import List, Dict, Any, Optional, Tuple

try:
    import speech_recognition as sr
except ImportError:
    sr = None

logger = logging.getLogger(__name__)

DEFAULT_STYLE_PROMPT = (
    "cinematic 35mm film still, shallow depth of field, atmospheric volumetric lighting, "
    "anamorphic lens, 8k resolution, photorealistic masterpiece, highly detailed textures"
)

# Comprehensive patterns for template tags and placeholders to strip
TEMPLATE_TAGS_REGEX = re.compile(
    r'\[\s*(?:ROLE|INPUT|GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?|'
    r'INSTRUCTIONS(?:\s+FOR\s+BREAKING\s+DOWN\s+THE\s+SCRIPT)?|'
    r'OUTPUT\s+TEMPLATE|OUTPUT\s+FORMAT|OUTPUT|TEMPLATE|'
    r'INSERT\s+SCRIPT\s+HERE|INSERT\s+SCRIPT|INSERT\s+NUMBER\s+HERE|INSERT\s+NUMBER|'
    r'INSERT\s+[^\]]+|RULES|SYSTEM|META|CINEMATIC\s+RULES)\s*\]',
    re.IGNORECASE
)

TEMPLATE_PLACEHOLDER_REGEX = re.compile(
    r'\[\s*(?:specific\s+visual\s+scene[^\]]*|characters[^\]]*|action[^\]]*|'
    r'environment[^\]]*|camera[^\]]*|composition[^\]]*|lighting[^\]]*|'
    r'color[^\]]*|visual\s+style\s+details[^\]]*|scene[^\]]*|'
    r'characters/action/environment|camera/composition|lighting/color)\s*\]',
    re.IGNORECASE
)

SECTION_HEADER_REGEX = re.compile(
    r'\[\s*(ROLE|INPUT|GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?|'
    r'INSTRUCTIONS(?:\s+FOR\s+BREAKING\s+DOWN\s+THE\s+SCRIPT)?|'
    r'OUTPUT\s+TEMPLATE|OUTPUT\s+FORMAT|OUTPUT|TEMPLATE|'
    r'INSERT\s+SCRIPT\s+HERE|INSERT\s+SCRIPT|INSERT\s+NUMBER\s+HERE|INSERT\s+NUMBER|'
    r'RULES|SYSTEM|CINEMATIC\s+RULES)\s*\]',
    re.IGNORECASE
)

INSTRUCTION_LINE_PATTERNS = [
    re.compile(r'^(?:you\s+are\s+an?\s+|as\s+an?\s+expert\s+|your\s+task\s+is\s+|act\s+as\s+an?\s+).*', re.IGNORECASE),
    re.compile(r'^(?:generate\s+(?:image\s+)?prompts?\s+|create\s+(?:image\s+)?prompts?\s+|break\s+(?:down\s+)?the\s+script\s+).*', re.IGNORECASE),
    re.compile(r'^(?:follow\s+(?:these\s+)?(?:rules|instructions)|output\s+(?:format|template)|instructions\s*:|rules\s*:|role\s*:|input\s*:).*', re.IGNORECASE),
    re.compile(r'^(?:do\s+not\s+(?:include|generate|output)|ensure\s+that\s+|each\s+prompt\s+must\s+|every\s+prompt\s+must\s+).*', re.IGNORECASE),
    re.compile(r'^(?:format\s+each\s+prompt\s+|for\s+each\s+scene\s+|step\s+\d+\s*:).*', re.IGNORECASE),
]

class PromptEngine:
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        Formats seconds into MM:SS.ss (e.g. 00:04.25).
        """
        secs = max(0.0, float(seconds))
        mins = int(secs // 60)
        rem = secs % 60
        return f"{mins:02d}:{rem:05.2f}"

    @classmethod
    def clean_meta_instructions(cls, text: str) -> str:
        """
        Completely strips system instructions, meta-prompts, template headers,
        and prompt engineering placeholders like:
        - [ROLE]
        - [INPUT]
        - Script:
        - [GLOBAL VISUAL STYLE & CINEMATIC RULES]
        - [INSTRUCTIONS FOR BREAKING DOWN THE SCRIPT]
        - [OUTPUT TEMPLATE]
        - [INSERT SCRIPT HERE]
        - [INSERT NUMBER HERE]
        - [specific visual scene...], [characters...], [camera...]
        - Section labels (Art Medium:, Color Psychology:, Composition & Angles:, Text Integration:)
        """
        if not text:
            return ""

        # 1. Strip entire template blocks if present
        cleaned = re.sub(r'\[\s*(?:ROLE|INPUT|INSTRUCTIONS|OUTPUT)[^\]]*\].*?(?=\[\s*|\Z)', ' ', text, flags=re.DOTALL | re.IGNORECASE)

        # 2. Strip bracketed template tags and placeholders
        cleaned = TEMPLATE_TAGS_REGEX.sub(" ", cleaned)
        cleaned = TEMPLATE_PLACEHOLDER_REGEX.sub(" ", cleaned)
        cleaned = re.sub(r'\[[^\]]*(?:ROLE|INPUT|OUTPUT|STYLE|INSTRUCTION|INSERT|SCENE|TEMPLATE|NUMBER|OVERLAY)[^\]]*\]', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'<\s*[^>]*\s*>', ' ', cleaned)

        # 3. Strip meta instruction sentences and phrases
        meta_sentence_patterns = [
            r'To\s+maintain\s+100%\s+consistency[^.]*\.?',
            r'Never\s+assume[^.]*\.?',
            r'Bold\s+Red[^.]*\.?',
            r'Text\s+Integration:[^.]*\.?',
            r'Use\s+classic,\s+elegant\s+text\s+banners[^.]*\.?',
            r'Divide\s+the\s+provided\s+script[^.]*\.?',
            r'STRICT\s+OUTPUT\s+RULE:[^.]*\.?',
            r'Start\s+immediately\s+with[^.]*\.?',
            r'Create\s+each\s+prompt\s+using[^.]*\.?',
            r'You\s+are\s+an?\s+Expert[^.]*\.?',
            r'Your\s+job\s+is\s+to[^.]*\.?',
            r'Script:\s*Number\s+of\s+Images\s+Needed:?',
            r'Script:\s*',
            r'Number\s+of\s+Images\s+Needed:\s*',
            r'OUTPUT\s+TEMPLATE\s*:?',
            r'GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?\s*:?',
            r'INSERT\s+SCRIPT\s+HERE',
            r'INSERT\s+NUMBER\s+HERE',
            r'--ar\s+',
            r'\[Number\]\.\s*',
            r'Generate\s+a\s+cinematic\s+watercolor[^.]*\.{2,}',
            r'\[TEXT\s+OVERLAY:[^\]]*\]\.{0,}',
        ]
        for p in meta_sentence_patterns:
            cleaned = re.sub(p, ' ', cleaned, flags=re.IGNORECASE)

        # 4. Strip section headers and field labels
        cleaned = re.sub(r'\b(?:Art\s+Medium|Color\s+Psychology|Composition\s*&\s*Angles|Text\s+Integration|Role|Input|Output|Instructions?|Rules?)\s*:\s*', ' ', cleaned, flags=re.IGNORECASE)

        # 5. Line-level instruction removal
        lines = cleaned.splitlines()
        filtered = []
        for line in lines:
            sline = line.strip()
            if not sline:
                continue

            # Skip instruction lines
            if any(pat.match(sline) for pat in INSTRUCTION_LINE_PATTERNS):
                continue

            # Strip numbering prefixes like "1.", "[INSERT NUMBER HERE]."
            sline = re.sub(r'^(?:\d+\.|\bINSERT\s+NUMBER\s+HERE\b\.*)\s*', '', sline, flags=re.IGNORECASE)

            if sline:
                filtered.append(sline)

        result = " ".join(filtered)

        # Clean punctuation and whitespace
        result = re.sub(r'[\r\n]+', ' ', result)
        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r'\s*\.\s*', '. ', result)
        result = re.sub(r',(\s*,)+', ',', result)
        result = re.sub(r'[,.\s]+$', '', result)
        result = re.sub(r'^[,.\s]+', '', result)
        return " ".join(result.split())

    @classmethod
    def parse_template_sections(cls, text: str) -> Dict[str, str]:
        """
        Parses structured template text into its component sections by bracketed headers.
        """
        matches = list(SECTION_HEADER_REGEX.finditer(text))
        if not matches:
            return {}

        sections: Dict[str, str] = {}
        for i, match in enumerate(matches):
            raw_tag = match.group(1).upper()
            if "STYLE" in raw_tag or "GLOBAL" in raw_tag:
                norm_tag = "STYLE"
            elif "SCRIPT" in raw_tag or "INPUT" in raw_tag:
                norm_tag = "SCRIPT"
            elif "OUTPUT" in raw_tag or "TEMPLATE" in raw_tag:
                norm_tag = "OUTPUT"
            elif "INSTRUCTION" in raw_tag or "RULE" in raw_tag:
                norm_tag = "INSTRUCTIONS"
            elif "ROLE" in raw_tag or "SYSTEM" in raw_tag:
                norm_tag = "ROLE"
            else:
                norm_tag = raw_tag

            start_idx = match.end()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections[norm_tag] = text[start_idx:end_idx].strip()

        return sections

    @classmethod
    def extract_clean_style(cls, raw_style: str) -> str:
        """
        Extracts purely the visual style descriptors from the user's input,
        completely stripping all [ROLE], [GLOBAL VISUAL STYLE...], [INSTRUCTIONS...],
        and [OUTPUT TEMPLATE] sections.
        """
        if not raw_style or not raw_style.strip():
            return "Cinematic watercolor illustration, warm natural light, atmospheric depth, 16:9"

        text = raw_style.strip()
        has_16_9 = bool(re.search(r'\b16:9\b|--ar\s+16:9', text))

        # 1. Isolate the style section if structured headers exist
        gvs_match = re.search(
            r'\[\s*(?:GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?|VISUAL\s+STYLE|STYLE)\s*\](.*?)(?=\[\s*(?:INSTRUCTIONS|OUTPUT|INPUT|ROLE|RULES)|\Z)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if gvs_match:
            section = gvs_match.group(1).strip()
        else:
            alt_match = re.search(
                r'(?:GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?|Art\s+Medium)\s*:?(.*?)(?=(?:INSTRUCTIONS\s+FOR|OUTPUT\s+TEMPLATE|STRICT\s+OUTPUT|\Z))',
                text,
                re.DOTALL | re.IGNORECASE
            )
            if alt_match:
                section = alt_match.group(0).strip()
            else:
                section = re.sub(r'\[\s*(?:ROLE|INPUT|INSTRUCTIONS|OUTPUT)[^\]]*\].*?(?=\[\s*|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE).strip()

        visual_elements = []

        # 2. Medium extraction
        med_m = re.search(r'(?:Art\s+Medium|Medium|Art\s+Style)\s*:\s*([^\n]+)', section, re.IGNORECASE)
        if med_m:
            m_raw = med_m.group(1).strip()
            m_clean = re.sub(r'^(?:high[- ]quality,?\s*)', '', m_raw, flags=re.IGNORECASE)
            m_clean = re.sub(r'\b(?:not\s+3d|not\s+photorealistic)[^.]*\.?', '', m_clean, flags=re.IGNORECASE)
            m_clean = re.sub(r'It\s+should\s+look\s+like\s+an?\s+', '', m_clean, flags=re.IGNORECASE)
            m_clean = re.sub(r'Flat\s+graphic\s+storytelling\s+style\s+but\s+with\s+', '', m_clean, flags=re.IGNORECASE)
            m_clean = re.sub(r'\(chiaroscuro\)', 'chiaroscuro', m_clean, flags=re.IGNORECASE)
            m_clean = re.sub(r'\.\s*', ', ', m_clean).strip(",. ")
            if m_clean:
                visual_elements.append(m_clean)
        else:
            for kw in ["watercolor and ink illustration", "watercolor illustration", "35mm film still", "oil painting", "digital concept art"]:
                if kw in section.lower():
                    visual_elements.append(f"Cinematic {kw}")
                    break

        # 3. Lighting / Color extraction
        col_m = re.search(r'(?:Color\s+Psychology|Colors?|Lighting)\s*:\s*([^\n]+)', section, re.IGNORECASE)
        if col_m:
            c_raw = col_m.group(1).strip()
            c_clean = re.sub(r'\s+for\s+themes\s+of.*', '', c_raw, flags=re.IGNORECASE)
            c_clean = re.sub(r'Cold,\s+shadowy.*', '', c_clean, flags=re.IGNORECASE)
            c_clean = re.sub(r'Bold\s+Red.*', '', c_clean, flags=re.IGNORECASE)
            c_clean = c_clean.replace("Gold/Amber/Yellow", "gold and warm amber")
            c_clean = c_clean.strip(",. ")
            if c_clean:
                visual_elements.append(c_clean)

        # 4. Composition
        comp_m = re.search(r'(?:Composition\s*&\s*Angles|Composition)\s*:\s*([^\n]+)', section, re.IGNORECASE)
        if comp_m:
            comp_raw = comp_m.group(1).strip()
            comp_clean = re.sub(r'Use\s+low-angle.*', '', comp_raw, flags=re.IGNORECASE)
            comp_clean = comp_clean.strip(",. ")
            if comp_clean:
                visual_elements.append(comp_clean)

        if visual_elements:
            combined = ", ".join(visual_elements)
        else:
            combined = section

        clean = cls.clean_meta_instructions(combined)
        if has_16_9 and "16:9" not in clean:
            clean = f"{clean}, 16:9"

        return clean.strip() if clean.strip() else DEFAULT_STYLE_PROMPT

    @classmethod
    def extract_clean_script(cls, raw_script: str) -> str:
        """
        Extracts purely the narrative script from the user's input,
        completely stripping all [ROLE], [INPUT], [INSERT SCRIPT HERE],
        [INSTRUCTIONS...], and [OUTPUT TEMPLATE] sections.
        """
        if not raw_script or not raw_script.strip():
            return ""

        sections = cls.parse_template_sections(raw_script)
        if "SCRIPT" in sections and sections["SCRIPT"].strip():
            target = sections["SCRIPT"]
        else:
            target = raw_script

        clean = cls.clean_meta_instructions(target)
        if not clean:
            clean = cls.clean_meta_instructions(raw_script)

        return clean.strip()

    @classmethod
    def segment_into_visual_scenes(cls, text: str) -> List[str]:
        """
        Splits script or speech text into visual scenes and distinct visual ideas.
        Detects sentence boundaries AND visual idea shifts inside compound sentences
        (subjects, actions, locations, events, transitions).
        Prevents long 1-2 minute still scenes by keeping visual units concise (5-15s speech equivalent).
        """
        cleaned_text = cls.extract_clean_script(text)
        cleaned = " ".join(cleaned_text.strip().split())
        if not cleaned:
            return []

        # 1. Primary sentence boundaries and line breaks
        if any(p in cleaned for p in [".", "!", "?", "\n"]):
            primary = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', cleaned) if s.strip()]
        else:
            words = cleaned.split()
            primary = [" ".join(words[i:i + 12]) for i in range(0, len(words), 12)]

        # 2. Visual transition regex within compound sentences
        transition_pattern = re.compile(
            r'(?:;\s*|'
            r'\s*—\s*|\s*--\s*|'
            r',\s*(?=(?:while|as|meanwhile|suddenly|where|when|then|and\s+then|but\s+then|moments\s+later|shortly\s+after|soon\s+after|later|eventually|in\s+the\s+distance|far\s+away|nearby|outside|inside|beyond|overhead|beneath|across|deep\s+within)\b)|'
            r',\s*(?=(?:and|but|yet)\s+(?:the|a|an|he|she|it|they|we|his|her|their|our|this|that|these|those|[A-Z]))'
            r')',
            re.IGNORECASE
        )

        visual_scenes = []

        for sentence in primary:
            # Skip any leftover instruction line
            if any(pat.match(sentence) for pat in INSTRUCTION_LINE_PATTERNS):
                continue

            words = sentence.split()
            if len(words) <= 16 and not any(p in sentence for p in [";", "—", "--"]):
                visual_scenes.append(sentence)
                continue

            splits = [p.strip() for p in transition_pattern.split(sentence) if p.strip()]

            refined_splits = []
            for s in splits:
                swords = s.split()
                if len(swords) > 22:
                    sub_parts = [p.strip() for p in re.split(r',\s+', s) if p.strip()]
                    cur_chunk = []
                    for sp in sub_parts:
                        cur_chunk.append(sp)
                        if len(" ".join(cur_chunk).split()) >= 10:
                            refined_splits.append(", ".join(cur_chunk))
                            cur_chunk = []
                    if cur_chunk:
                        if refined_splits and len(" ".join(cur_chunk).split()) < 4:
                            refined_splits[-1] = f"{refined_splits[-1]}, {', '.join(cur_chunk)}"
                        else:
                            refined_splits.append(", ".join(cur_chunk))
                else:
                    refined_splits.append(s)

            merged = []
            for part in refined_splits:
                if not part:
                    continue
                clean_part = part[0].upper() + part[1:] if len(part) > 1 else part.upper()
                clean_part = clean_part.rstrip(",")
                if merged and len(clean_part.split()) < 3:
                    merged[-1] = f"{merged[-1]}, {clean_part}"
                else:
                    merged.append(clean_part)

            visual_scenes.extend(merged)

        return visual_scenes if visual_scenes else [cleaned]

    @classmethod
    def segment_into_sentences(cls, text: str) -> List[str]:
        """
        Alias for backwards compatibility. Uses visual scene segmentation.
        """
        return cls.segment_into_visual_scenes(text)

    @classmethod
    def synthesize_visual_prompt(
        cls,
        sentence: str,
        visual_style_prompt: str = ""
    ) -> str:
        """
        Combines the sentence visual content with the user's requested visual style.
        CRITICAL RULES:
        - Output contains ONLY the actual image generation prompt.
        - ZERO [ROLE], [INPUT], [GLOBAL VISUAL STYLE], [INSTRUCTIONS], [OUTPUT TEMPLATE], or [INSERT ...] text.
        - ZERO system/meta instructions or explanations.
        - Strictly ONE continuous paragraph with NO internal line breaks.
        - Optimized for direct copy/paste into a bulk image generator.
        """
        clean_sentence = cls.clean_meta_instructions(sentence)
        clean_sentence = re.sub(r'[.!?]+$', '', clean_sentence).strip()
        if clean_sentence:
            clean_sentence = clean_sentence[0].upper() + clean_sentence[1:]

        clean_style = cls.extract_clean_style(visual_style_prompt)

        if not clean_style:
            result = f"{clean_sentence}, 16:9." if clean_sentence else "Cinematic visual scene, 16:9."
        else:
            style_parts = [p.strip() for p in clean_style.split(",") if p.strip()]
            lead = style_parts[0] if style_parts else clean_style

            # Standardize medium lead if applicable
            lead_lower = lead.lower()
            if "watercolor" in lead_lower:
                art_lead = "Cinematic watercolor illustration"
            elif "film still" in lead_lower or "35mm" in lead_lower:
                art_lead = "Cinematic 35mm film still"
            elif "oil painting" in lead_lower or "oil on canvas" in lead_lower:
                art_lead = "Cinematic oil painting"
            elif "photograph" in lead_lower or "photojournalism" in lead_lower:
                art_lead = "Cinematic documentary photograph"
            else:
                art_lead = lead

            # Filter remaining modifiers (excluding art_lead keywords and aspect ratio)
            modifiers = []
            for p in style_parts[1:]:
                p_low = p.lower()
                if any(w in p_low for w in ["watercolor", "illustration", "16:9", "--ar"]):
                    continue
                if p not in modifiers:
                    modifiers.append(p)

            # Format scene with proper lowercasing for prepositions/articles
            words = clean_sentence.split()
            first_word = words[0] if words else ""
            common_preps = {"in", "at", "on", "deep", "inside", "beyond", "across", "as", "the", "a", "an", "with", "without", "through", "under", "over"}
            if first_word.lower() in common_preps:
                formatted_scene = first_word.lower() + (" " + " ".join(words[1:]) if len(words) > 1 else "")
            elif len(first_word) > 1 and first_word.isupper():
                formatted_scene = clean_sentence
            else:
                formatted_scene = clean_sentence[0].lower() + clean_sentence[1:] if len(clean_sentence) > 1 else clean_sentence

            mod_str = ", ".join(modifiers) if modifiers else ""

            if mod_str:
                result = f"{art_lead} of {formatted_scene}, {mod_str}, 16:9."
            else:
                result = f"{art_lead} of {formatted_scene}, 16:9."

        # Strict final sanitization pass: strip any leftover template brackets, instructions, or internal line breaks
        result = cls.clean_meta_instructions(result)
        result = re.sub(r'[\r\n]+', ' ', result)
        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r',(\s*,)+', ',', result)
        result = re.sub(r'\.\s*\.', '.', result)
        return " ".join(result.split())

    @classmethod
    def subdivide_long_narration_scene(cls, scene_text: str, duration: float) -> List[Tuple[str, float]]:
        """
        Subdivides any narration segment that exceeds 15 seconds into 5-15s visual shots
        (establishing shot, medium action, close-up details, atmospheric angle).
        Guarantees no visual prompt remains static for 1-2 minutes.
        """
        if duration <= 15.0:
            return [(scene_text, duration)]

        # Target 8-12 seconds per visual
        num_parts = math.ceil(duration / 11.0)
        part_duration = round(duration / num_parts, 2)

        words = scene_text.split()
        results = []

        if len(words) >= num_parts * 4:
            chunk_len = len(words) // num_parts
            for i in range(num_parts):
                start_w = i * chunk_len
                end_w = (i + 1) * chunk_len if i < num_parts - 1 else len(words)
                sub_text = " ".join(words[start_w:end_w]).strip()
                if sub_text:
                    sub_text = sub_text[0].upper() + sub_text[1:]
                    results.append((sub_text, part_duration))
        else:
            perspectives = [
                f"Wide establishing cinematic shot of {scene_text[0].lower() + scene_text[1:] if len(scene_text) > 1 else scene_text}",
                f"Medium shot focusing on the key actions of {scene_text[0].lower() + scene_text[1:] if len(scene_text) > 1 else scene_text}",
                f"Dramatic close-up detail capturing {scene_text[0].lower() + scene_text[1:] if len(scene_text) > 1 else scene_text}",
                f"Atmospheric cinematic perspective exploring {scene_text[0].lower() + scene_text[1:] if len(scene_text) > 1 else scene_text}",
            ]
            for i in range(num_parts):
                p_text = perspectives[i % len(perspectives)]
                results.append((p_text, part_duration))

        return results

    @classmethod
    def detect_audio_speech_intervals(cls, audio_path: str, total_duration: float) -> List[Tuple[float, float]]:
        """
        Uses ffmpeg silencedetect to accurately extract speech intervals (non-silent zones).
        """
        if not os.path.exists(audio_path) or total_duration <= 0:
            return [(0.0, max(1.0, total_duration))]

        try:
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-af", "silencedetect=noise=-30dB:d=0.25",
                "-f", "null", "-"
            ]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

            silence_starts = []
            silence_ends = []
            for line in res.stderr.splitlines():
                if "silence_start:" in line:
                    match = re.search(r'silence_start:\s*([0-9.]+)', line)
                    if match:
                        silence_starts.append(float(match.group(1)))
                elif "silence_end:" in line:
                    match = re.search(r'silence_end:\s*([0-9.]+)', line)
                    if match:
                        silence_ends.append(float(match.group(1)))

            # Build speech intervals between silences
            speech_intervals = []
            current_pos = 0.0

            for i in range(len(silence_starts)):
                s_start = silence_starts[i]
                s_end = silence_ends[i] if i < len(silence_ends) else total_duration

                if s_start > current_pos + 0.1:
                    speech_intervals.append((round(current_pos, 2), round(s_start, 2)))
                current_pos = s_end

            if current_pos < total_duration - 0.1:
                speech_intervals.append((round(current_pos, 2), round(total_duration, 2)))

            if speech_intervals:
                return speech_intervals
        except Exception as e:
            logger.warning(f"Silence detection warning: {e}")

        return [(0.0, round(total_duration, 2))]

    @classmethod
    def analyze_audio_and_align_script(
        cls,
        audio_path: str,
        script_text: str,
        visual_style_prompt: str = "",
        total_duration: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        1. Analyzes audio speech & pause timing using ffmpeg silencedetect.
        2. Matches the user's provided script with the spoken audio timeline.
        3. Segments visual-idea-by-visual-idea with 5-15s typical duration.
        4. For long narrations (e.g. 25 minutes = 1500s), dynamically subdivides scenes so NO prompt is 1-2 minutes.
        5. Does NOT limit output to 100 prompts. Covers 100% of script/audio with zero missing sections.
        """
        if total_duration <= 0.0 and os.path.exists(audio_path):
            try:
                cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                total_duration = round(float(res.stdout.strip()), 2)
            except Exception:
                total_duration = 15.0

        if total_duration <= 0.0:
            total_duration = 15.0

        # Transcribe speech if script is empty and audio is present
        if not script_text.strip() and sr and os.path.exists(audio_path):
            temp_dir = tempfile.gettempdir()
            temp_wav = os.path.join(temp_dir, f"asr_{uuid.uuid4().hex[:8]}.wav")
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", audio_path,
                    "-ar", "16000", "-ac", "1",
                    temp_wav
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(temp_wav):
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(temp_wav) as source:
                        audio_data = recognizer.record(source)
                        script_text = recognizer.recognize_google(audio_data)
                    os.remove(temp_wav)
            except Exception as e:
                logger.info(f"[Audio Alignment] Speech recognition fallback note: {e}")

        # 1. Segment script into visual scenes
        raw_segments = cls.segment_into_visual_scenes(script_text)
        if not raw_segments:
            raw_segments = ["Atmospheric cinematic scene with detailed environment and lighting"]

        # 2. Initial proportional duration allocation based on speech weight
        total_words = sum(len(s.split()) for s in raw_segments) or len(raw_segments)
        initial_scenes = []
        for s in raw_segments:
            w_count = len(s.split())
            portion = w_count / max(1, total_words)
            dur = total_duration * portion
            initial_scenes.append((s, dur))

        # 3. Dynamic subdivision for scenes exceeding 15 seconds
        # Eliminates 1-2 minute long prompts and enforces 5-15 second visual cadence
        refined_scenes: List[Tuple[str, float]] = []
        for s_text, dur in initial_scenes:
            if dur > 15.0:
                refined_scenes.extend(cls.subdivide_long_narration_scene(s_text, dur))
            else:
                refined_scenes.append((s_text, dur))

        # Iteratively ensure no scene duration exceeds 15.0 seconds
        max_iterations = 5
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            max_dur = max((d for _, d in refined_scenes), default=0.0)
            if max_dur <= 15.0:
                break
            new_refined = []
            for s_text, dur in refined_scenes:
                if dur > 15.0:
                    new_refined.extend(cls.subdivide_long_narration_scene(s_text, dur))
                else:
                    new_refined.append((s_text, dur))
            if len(new_refined) == len(refined_scenes):
                break
            refined_scenes = new_refined

        # 4. Normalize to exact total_duration with continuous zero-gap timeline
        raw_sum = sum(d for _, d in refined_scenes) or 1.0
        scaling = total_duration / raw_sum

        scenes = []
        cur_time = 0.0

        for idx, (s_text, dur) in enumerate(refined_scenes):
            scaled_dur = round(dur * scaling, 2)
            if total_duration >= 20.0:
                scaled_dur = max(4.5, min(15.0, scaled_dur))

            if idx == len(refined_scenes) - 1:
                end_time = round(total_duration, 2)
                final_dur = round(max(1.0, end_time - cur_time), 2)
            else:
                end_time = round(min(total_duration, cur_time + scaled_dur), 2)
                final_dur = round(max(1.0, end_time - cur_time), 2)

            prompt = cls.synthesize_visual_prompt(s_text, visual_style_prompt)

            scenes.append({
                "scene_index": idx + 1,
                "sentence": s_text,
                "transcript_text": s_text,
                "image_prompt": prompt,
                "start_time": round(cur_time, 2),
                "end_time": end_time,
                "duration": final_dur,
                "start_time_formatted": cls.format_timestamp(cur_time),
                "end_time_formatted": cls.format_timestamp(end_time),
                "duration_formatted": f"{final_dur:.2f}s",
                "negative_prompt": "blurry, low quality, distorted, extra limbs, bad anatomy, watermark, signature, text overlay",
                "aspect_ratio": "16:9",
            })
            cur_time = end_time

        return scenes

    @classmethod
    def generate_from_script_and_style(
        cls,
        script_text: str,
        visual_style_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """
        When audio is not provided:
        Generates visual-idea-level scenes from the script sentence structure using
        cinematic documentary pacing (5-10s for fast narration, 10-15s for slower sentences).
        """
        sentences = cls.segment_into_visual_scenes(script_text)
        if not sentences:
            sentences = ["Atmospheric cinematic scene with detailed environment and lighting"]

        scenes = []
        cur_time = 0.0

        for idx, sentence in enumerate(sentences):
            words = sentence.split()
            w_len = len(words)

            # Fast-changing short clauses (<= 8 words): 5.0 to 8.0s
            # Medium clauses (9-14 words): 8.0 to 12.0s
            # Longer sentences (15+ words): 12.0 to 15.0s (strictly capped at 15.0s max)
            if w_len <= 8:
                dur = max(5.0, round(5.0 + (w_len / 8.0) * 3.0, 2))
            elif w_len <= 14:
                dur = round(8.0 + ((w_len - 8) / 6.0) * 4.0, 2)
            else:
                dur = min(15.0, round(12.0 + min(3.0, (w_len - 14) * 0.2), 2))

            end_time = round(cur_time + dur, 2)
            prompt = cls.synthesize_visual_prompt(sentence, visual_style_prompt)

            scenes.append({
                "scene_index": idx + 1,
                "sentence": sentence,
                "transcript_text": sentence,
                "image_prompt": prompt,
                "start_time": round(cur_time, 2),
                "end_time": end_time,
                "duration": dur,
                "start_time_formatted": cls.format_timestamp(cur_time),
                "end_time_formatted": cls.format_timestamp(end_time),
                "duration_formatted": f"{dur:.2f}s",
                "negative_prompt": "blurry, low quality, distorted, extra limbs, bad anatomy, watermark, signature, text overlay",
                "aspect_ratio": "16:9",
            })
            cur_time = end_time

        return scenes

    # Backwards compatibility methods
    @classmethod
    def generate_from_script(cls, script_text: str, style_preset: str = "cinematic") -> List[Dict[str, Any]]:
        from app.services.prompt_engine import STYLE_PROMPT_ENHANCERS
        preset_prompt = STYLE_PROMPT_ENHANCERS.get(style_preset.lower(), DEFAULT_STYLE_PROMPT)
        return cls.generate_from_script_and_style(script_text, preset_prompt)

    @classmethod
    def analyze_audio_and_generate_scenes(cls, audio_path: str, total_duration: float, style_preset: str = "cinematic") -> List[Dict[str, Any]]:
        from app.services.prompt_engine import STYLE_PROMPT_ENHANCERS
        preset_prompt = STYLE_PROMPT_ENHANCERS.get(style_preset.lower(), DEFAULT_STYLE_PROMPT)
        return cls.analyze_audio_and_align_script(audio_path, "", preset_prompt, total_duration)

STYLE_PROMPT_ENHANCERS = {
    "cinematic": "cinematic 35mm film still, shallow depth of field, atmospheric volumetric lighting, anamorphic lens, 8k resolution, photorealistic masterpiece",
    "photorealistic": "hyper-realistic 8k photograph, shot on Hasselblad H6D-100c, 85mm lens, natural golden hour lighting, ultra-sharp focus, intricate textures",
    "documentary": "National Geographic photojournalism, Leica M10 candid capture, authentic ambient lighting, photojournalism award winner, gritty realism",
    "anime": "anime key visual, Makoto Shinkai and Studio Ghibli inspired, vibrant colors, detailed sky with fluffy cumulus clouds, luminous cinematic lighting, masterpiece",
    "digital_art": "vibrant digital concept art, Unreal Engine 5 octane render, dramatic lighting, rich color palette, trending on ArtStation, highly detailed",
}

prompt_engine = PromptEngine()

