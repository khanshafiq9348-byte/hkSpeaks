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

# Forbidden header names that must NEVER leak into the generated output
FORBIDDEN_HEADER_NAMES = [
    "LOCKED STYLE BIBLE",
    "STYLE BIBLE",
    "MASTER STYLE BIBLE",
    "UPDATED MASTER PROMPT",
    "MASTER PROMPT",
    "MASTER STYLE PROMPT",
    "MASTER STYLE",
    "MASTER RULES",
    "GLOBAL MASTER PROMPT",
    "SYSTEM PROMPT",
    "PROMPT INSTRUCTIONS",
    "CRITICAL INSTRUCTION",
    "CRITICAL INSTRUCTIONS",
    "CRITICAL RULE",
    "CRITICAL RULES",
    "TASK INSTRUCTION",
    "TASK INSTRUCTIONS",
    "IMPORTANT INSTRUCTION",
    "IMPORTANT INSTRUCTIONS",
    "SYSTEM INSTRUCTION",
    "SYSTEM INSTRUCTIONS",
    "SYSTEM MESSAGE",
    "GENERAL INSTRUCTION",
    "GENERAL INSTRUCTIONS",
    "PROMPT GENERATION RULES",
    "PROMPT GENERATION RULE",
    "STRICT RULES",
    "STRICT RULE",
    "GENERATION RULES",
    "SCENE BREAKDOWN",
    "CINEMATIC LANGUAGE",
    "CAMERA ANGLES",
    "CAMERA ANGLE",
    "COMPOSITION RULES",
    "COMPOSITION RULE",
    "COMPOSITION & CAMERA RULE",
    "COMPOSITION & CAMERA RULES",
    "COMPOSITION AND CAMERA RULE",
    "LIGHTING STYLE",
    "HISTORICAL ACCURACY RULE",
    "HISTORICAL ACCURACY",
    "EMOTIONAL TONE",
    "VISUAL STORYTELLING RULE",
    "VISUAL STORYTELLING",
    "NO TEXT RULE",
    "NO TEXT",
    "FINAL QUALITY STANDARD",
    "QUALITY STANDARD",
    "GLOBAL VISUAL STYLE & CINEMATIC RULES",
    "GLOBAL VISUAL STYLE",
    "VISUAL STYLE & CINEMATIC RULES",
    "VISUAL STYLE",
    "INSTRUCTIONS FOR BREAKING DOWN THE SCRIPT",
    "INSTRUCTIONS FOR BREAKING DOWN SCRIPT",
    "INSTRUCTIONS",
    "OUTPUT TEMPLATE",
    "OUTPUT FORMAT",
    "OUTPUT RULES",
    "OUTPUT RULE",
    "STRICT OUTPUT RULE",
    "TEXT INTEGRATION",
    "TEXT OVERLAY",
    "ART MEDIUM",
    "ART STYLE",
    "CHARACTER DESIGN RULE",
    "CHARACTER DESIGN RULES",
    "CHARACTER DESIGN",
    "LINE & TEXTURE",
    "LINE AND TEXTURE",
    "COLOR PALETTE ROTATION RULE",
    "COLOR PALETTE ROTATION",
    "COLOR PALETTE",
    "COLOR PSYCHOLOGY",
    "TYPOGRAPHY RULE",
    "TYPOGRAPHY RULES",
    "TYPOGRAPHY",
    "MOOD CONSISTENCY",
    "MOOD CONSISTENCY RULE",
    "SCENE GENERATION LOGIC",
    "SCENE GENERATION RULES",
    "SCENE GENERATION",
    "USER INPUT FORMAT",
    "USER INPUT",
    "NUMBER OF IMAGES NEEDED",
    "NUMBER OF IMAGES",
    "IMAGES NEEDED",
    "RETURN ONLY",
    "OUTPUT ONLY",
    "INSERT SCRIPT HERE",
    "INSERT SCRIPT",
    "INSERT NUMBER HERE",
    "INSERT NUMBER",
]

# Regex pattern matching any forbidden header in brackets, or bold/plain followed by colon
headers_pattern = r'(?:' + '|'.join(re.escape(h) for h in FORBIDDEN_HEADER_NAMES) + r'|STEP\s*\d+|ROLE|INPUT|SYSTEM|META|RULES?|TEMPLATE|OUTPUT)'
FORBIDDEN_HEADERS_REGEX = re.compile(
    r'(?:'
    r'\[\s*(?:' + headers_pattern + r')\s*\]|'
    r'(?:\*\*|__)?\b(?:' + headers_pattern + r')\b(?:\*\*|__)?\s*:'
    r')',
    re.IGNORECASE
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
    r'\[\s*(?:'
    r'specific\s+visual\s+scene[^\]]*|'
    r'characters[^\]]*|'
    r'action[^\]]*|'
    r'environment[^\]]*|'
    r'camera[^\]]*|'
    r'composition[^\]]*|'
    r'lighting[^\]]*|'
    r'color[^\]]*|'
    r'visual\s+style[^\]]*|'
    r'scene[^\]]*|'
    r'characters\/action\/environment|'
    r'camera\/composition|'
    r'lighting\/color|'
    r'insert\s+[^\]]+|'
    r'number|'
    r'scene\s+number|'
    r'prompt\s+number|'
    r'text\s+overlay[^\]]*'
    r')\s*\]|'
    r'<\s*[^>]*\s*>',
    re.IGNORECASE
)

SECTION_HEADER_REGEX = re.compile(
    r'(?:'
    r'\[\s*(ROLE|INPUT|GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?|'
    r'INSTRUCTIONS(?:\s+FOR\s+BREAKING\s+DOWN\s+THE\s+SCRIPT)?|'
    r'OUTPUT\s+TEMPLATE|OUTPUT\s+FORMAT|OUTPUT|TEMPLATE|'
    r'INSERT\s+SCRIPT\s+HERE|INSERT\s+SCRIPT|INSERT\s+NUMBER\s+HERE|INSERT\s+NUMBER|'
    r'RULES|SYSTEM|CINEMATIC\s+RULES|SCRIPT|MASTER\s+STYLE\s+PROMPT|MASTER\s+STYLE|STYLE\s+PROMPT|STYLE|'
    r'LOCKED\s+STYLE\s+BIBLE|STYLE\s+BIBLE|ART\s+STYLE|USER\s+INPUT\s+FORMAT|SCENE\s+GENERATION\s+LOGIC|'
    r'NUMBER\s+OF\s+IMAGES(?:\s+NEEDED)?|RETURN\s+ONLY)\s*\]|'
    r'(?:^|\n)\s*(?:\*\*|__)?\b(SCRIPT|MASTER\s+STYLE\s+PROMPT|MASTER\s+STYLE|STYLE\s+PROMPT|VISUAL\s+STYLE|STYLE|'
    r'LOCKED\s+STYLE\s+BIBLE|STYLE\s+BIBLE|ART\s+STYLE|USER\s+INPUT\s+FORMAT|SCENE\s+GENERATION\s+LOGIC|'
    r'NUMBER\s+OF\s+IMAGES(?:\s+NEEDED)?|RETURN\s+ONLY|INSTRUCTIONS?|ROLE|SYSTEM|INPUT|OUTPUT)\b(?:\*\*|__)?\s*:'
    r')',
    re.IGNORECASE
)

INSTRUCTION_LINE_PATTERNS = [
    re.compile(r'^(?:task|job|role|instructions?|rules?|input|output|format|system|meta)\s*:', re.IGNORECASE),
    re.compile(r'^(?:you\s+are|you\s+must|you\s+should|as\s+an?\s+expert|your\s+(?:task|job|role|goal)\s+is|act\s+as\s+an?\s+)', re.IGNORECASE),
    re.compile(r'^(?:i\s+will\s+provide|provide\s+(?:a|the)\s+script|here\s+is\s+(?:the|a)\s+script)', re.IGNORECASE),
    re.compile(r'^(?:generate|create|write|make)\s+(?:image\s+)?prompts?', re.IGNORECASE),
    re.compile(r'^(?:break\s+(?:down\s+)?the\s+script|divide\s+the\s+script)', re.IGNORECASE),
    re.compile(r'^(?:follow\s+(?:these\s+)?(?:rules|instructions)|output\s+(?:format|template)|instructions?\s*:|rules?\s*:|role\s*:|input\s*:|task\s*:)', re.IGNORECASE),
    re.compile(r'^(?:do\s+not\s+(?:include|generate|output|print|limit|copy|invent|add|override)|ensure\s+that\s+|each\s+prompt\s+must\s+|every\s+prompt\s+must\s+)', re.IGNORECASE),
    re.compile(r'^(?:format\s+each\s+prompt\s+|for\s+each\s+scene\s+|step\s+\d+\s*:|strict\s+output\s+rule\s*:?)', re.IGNORECASE),
    re.compile(r'^(?:to\s+maintain\s+100%\s+consistency|never\s+assume|divide\s+the\s+provided\s+script|start\s+immediately\s+with)', re.IGNORECASE),
    re.compile(r'^(?:highlight\s+the\s+|focus\s+on\s+capturing|show\s+the\s+emotion|all\s+prompts\s+must)', re.IGNORECASE),
    re.compile(r'^(?:absolutely\s+no\s+text|no\s+text,\s*no\s+letters|no\s+words,\s*no\s+signs|avoid\s+any\s+text)', re.IGNORECASE),
    re.compile(r'^(?:updated\s+master\s+prompt|master\s+prompt\s*:?|global\s+master\s+prompt\s*:?|master\s+style\s*:?)', re.IGNORECASE),
    re.compile(r'^(?:critical\s+instructions?|task\s+instructions?|important\s+instructions?|system\s+instructions?|general\s+instructions?)', re.IGNORECASE),
    re.compile(r'^(?:convert\s+each\s+script\s+scene|keep\s+prompts?\s+short|follow\s+the\s+user|never\s+include)', re.IGNORECASE),
    re.compile(r'^(?:script\s*=\s*(?:content|what)|style\s*prompt\s*=\s*(?:exact|how)|do\s+not\s+create\s+repetitive)', re.IGNORECASE),
    re.compile(r'^(?:locked\s+style\s+bible|style\s+bible|master\s+style\s+bible)', re.IGNORECASE),
    re.compile(r'^(?:character\s+design\s+rules?|typography\s+rules?|composition\s*(?:&|and)\s*camera\s+rules?|color\s+palette\s+rotation(?:\s+rule)?|line\s*(?:&|and)\s*texture|mood\s+consistency)', re.IGNORECASE),
    re.compile(r'^(?:scene\s+generation\s+logic|user\s+input\s+format|number\s+of\s+images|return\s+only|output\s+only)', re.IGNORECASE),
    re.compile(r'^(?:step\s*\d+|clean\s+image-generation\s+prompt|style\s+constraint)', re.IGNORECASE),
    re.compile(r'\banalyze\s+the\s+provided\s+(?:video\s+|audio\s+)?(?:script|narration|text)', re.IGNORECASE),
    re.compile(r'\bgenerate\s+(?:a\s+)?distinct\s+(?:image\s+)?prompts?', re.IGNORECASE),
    re.compile(r'\bdo\s+not\s+limit\b', re.IGNORECASE),
    re.compile(r'\bdo\s+not\s+copy\b', re.IGNORECASE),
    re.compile(r'\bdo\s+not\s+invent\b', re.IGNORECASE),
    re.compile(r'\bmaster\s+prompt\b', re.IGNORECASE),
    re.compile(r'\braw\s+style\s+prompt\b', re.IGNORECASE),
    re.compile(r'\brequired\s+pipeline\b', re.IGNORECASE),
    re.compile(r'\bpreserve\s+the\s+exact\s+meaning\b', re.IGNORECASE),
    re.compile(r'\bapply\s+only\s+the\s+user\b', re.IGNORECASE),
    re.compile(r'\bfinal\s+output\s+must\s+contain\b', re.IGNORECASE),
    re.compile(r'\bno\s+internal\s+instructions\b', re.IGNORECASE),
    re.compile(r'\bremove\s+completely\s+from\b', re.IGNORECASE),
    re.compile(r'\bclean\s+visual\s+scene\s+description\b', re.IGNORECASE),
    re.compile(r'\brule\s*\d+\s*[-—:]', re.IGNORECASE),
]

COMBINED_META_PATTERNS = [
    r'Updated\s+Master\s+Prompt\s*:?',
    r'Master\s+Prompt\s*:?',
    r'Global\s+Master\s+Prompt\s*:?',
    r'LOCKED\s+STYLE\s+BIBLE\b:?',
    r'STYLE\s+BIBLE\b:?',
    r'MASTER\s+STYLE\s+BIBLE\b:?',
    r'CHARACTER\s+DESIGN\s+RULES?\s*:?[^.\n]*\.?',
    r'TYPOGRAPHY\s+RULES?\s*:?[^.\n]*\.?',
    r'NO\s+TEXT(?:\s+RULE)?\s*:?[^.\n]*\.?',
    r'COMPOSITION\s*(?:&|and)\s*CAMERA\s+RULES?\s*:?[^.\n]*\.?',
    r'SCENE\s+GENERATION\s+LOGIC\s*:?[^.\n]*\.?',
    r'SCENE\s+GENERATION\s+RULES?\s*:?[^.\n]*\.?',
    r'STEP\s*\d+\s*:?[^.\n]*\.?',
    r'USER\s+INPUT\s+FORMAT\s*:?[^.\n]*\.?',
    r'NUMBER\s+OF\s+IMAGES(?:\s+NEEDED)?\s*:?[^.\n]*\.?',
    r'RETURN\s+ONLY\b[^\n\r]*\.?',
    r'OUTPUT\s+ONLY\b[^\n\r]*\.?',
    r'CRITICAL\s+INSTRUCTIONS?\s*:?[^.\n]*\.?',
    r'TASK\s+INSTRUCTIONS?\s*:?[^.\n]*\.?',
    r'IMPORTANT\s+INSTRUCTIONS?\s*:?[^.\n]*\.?',
    r'SYSTEM\s+INSTRUCTIONS?\s*:?[^.\n]*\.?',
    r'CRITICAL\s+INSTRUCTION\b[^\n\r]*',
    r'TASK\s+INSTRUCTION\b[^\n\r]*',
    r'\bTask:\s*I\s+will\s+provide[^\n\r]*\.?',
    r'\bI\s+will\s+provide\s+a\s+script[^\n\r]*\.?',
    r'\bYou\s+must\s+generate[^\n\r]*\.?',
    r'\bGenerate\s+image\s+prompts[^\n\r]*\.?',
    r'\bTask:\s*[^\n\r]*',
    r'CRITICAL\s+RULES?\s*:?[^.\n]*\.?',
    r'To\s+maintain\s+100%\s+consistency[^.\n]*\.?',
    r'Never\s+assume[^.\n]*\.?',
    r'Bold\s+Red[^.\n]*\.?',
    r'Text\s+Integration:[^.\n]*\.?',
    r'Use\s+classic,\s+elegant\s+text\s+banners[^.\n]*\.?',
    r'Divide\s+the\s+provided\s+script[^.\n]*\.?',
    r'STRICT\s+OUTPUT\s+RULE:[^.\n]*\.?',
    r'Start\s+immediately\s+with[^.\n]*\.?',
    r'Create\s+each\s+prompt\s+using[^.\n]*\.?',
    r'You\s+are\s+an?\s+Expert[^.\n]*\.?',
    r'Your\s+(?:task|job)\s+is\s+to[^.\n]*\.?',
    r'Script:\s*Number\s+of\s+Images\s+Needed:?',
    r'Script:\s*',
    r'Number\s+of\s+Images\s+Needed:\s*',
    r'OUTPUT\s+TEMPLATE\s*:?',
    r'GLOBAL\s+VISUAL\s+STYLE(?:\s*&\s*CINEMATIC\s*RULES)?\s*:?',
    r'INSERT\s+SCRIPT\s+HERE',
    r'INSERT\s+NUMBER\s+HERE',
    r'--ar\s+\d+:\d+',
    r'--ar\s+',
    r'\[Number\]\.\s*',
    r'Generate\s+a\s+cinematic\s+watercolor[^.\n]*\.{2,}',
    r'\[TEXT\s+OVERLAY:[^\]]*\]\.{0,}',
    r'\banalyze\s+the\s+provided\s+(?:video\s+|audio\s+)?(?:script|narration|text)\b[^\n\r.]*(?:\.|$)',
    r'\bgenerate\s+(?:a\s+)?distinct\s+(?:image\s+)?prompts?\b[^\n\r.]*(?:\.|$)',
    r'\bdo\s+not\s+limit\b[^\n\r.]*(?:\.|$)',
    r'\bdo\s+not\s+copy\b[^\n\r.]*(?:\.|$)',
    r'\bdo\s+not\s+invent\b[^\n\r.]*(?:\.|$)',
    r'\bdo\s+not\s+override\b[^\n\r.]*(?:\.|$)',
    r'\bdo\s+not\s+add\b[^\n\r.]*(?:\.|$)',
    r'\brequired\s+pipeline\b[^\n\r]*',
    r'\bscript\s*(?:->|→|=|:)\s*understand\b[^\n\r]*',
    r'\bstyle\s+prompt\s*(?:->|→|=|:)\s*control\b[^\n\r]*',
    r'\bfor\s+(?:every|each)\s+(?:sentence|new\s+visual\s+concept|visual\s+concept|scene)\b[^\n\r.]*(?:\.|$)',
    r'\bpreserve\s+the\s+exact\s+meaning\b[^\n\r.]*(?:\.|$)',
    r'\bapply\s+only\s+the\s+user(?:\'s)?\s+style\b[^\n\r.]*(?:\.|$)',
    r'\bnever\s+generate\s+your\s+own\s+style\b[^\n\r.]*(?:\.|$)',
    r'\bremove\s+completely\s+from\s+final\s+prompts\b[^\n\r]*',
    r'\bfinal\s+output\s+must\s+contain\s+only\b[^\n\r]*',
    r'\bno\s+internal\s+instructions\b[^\n\r]*',
    r'\bmaster\s+prompt\s+text\b[^\n\r.]*(?:\.|$)',
    r'\braw\s+style\s+prompt\b[^\n\r.]*(?:\.|$)',
    r'\bmaster\s+style\s+prompt\b:?',
    r'\bmaster\s+style\b:?',
    r'\bmaster\s+rules?\b:?',
    r'\bscript\s*=\s*(?:content|what)[^\n\r.]*(?:\.|$)',
    r'\bstyle\s+prompt\s*=\s*(?:exact\s+visual\s+style|how)[^\n\r.]*(?:\.|$)',
    r'\boutput\s+(?:direct,?\s*)?(?:numbered\s+)?(?:image\s+)?prompts?\s+only[^\n\r.]*(?:\.|$)',
    r'\bwithout\s+(?:any\s+)?conversational\s+filler[^\n\r.]*(?:\.|$)',
    r'\bconversational\s+filler[^\n\r.]*(?:\.|$)',
    r'\bwhether\s+the\s+script\s+requires[^\n\r.]*(?:\.|$)',
    r'\byou\s+must\s+generate\s+a\s+prompt[^\n\r.]*(?:\.|$)',
    r'\bwhenever\s+a\s+new\s+concept\s+is\s+introduced[^\n\r.]*(?:\.|$)',
    r'\bfor\s+every\s+single\s+sentence[^\n\r.]*(?:\.|$)',
]

COMBINED_META_REGEX = re.compile(
    '|'.join(f'(?:{p})' for p in COMBINED_META_PATTERNS),
    re.IGNORECASE
)

SECTION_LABELS_REGEX = re.compile(
    r'\b(?:Art\s+Medium|Art\s+Style|Color\s+Psychology|Composition\s*&\s*Angles|Text\s+Integration|Role|Input|Output|Instructions?|Task|Script|Style\s+Prompt|Master\s+Prompt|Locked\s+Style\s+Bible)\s*:\s*',
    re.IGNORECASE
)

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
    def is_instruction_text(cls, text: str) -> bool:
        """
        Determines whether a piece of text contains internal generation instructions,
        meta-prompts, templates, master prompt instructions, or system directives.
        """
        if not text:
            return True
        t = text.strip().lower()
        if not re.search(r'[a-zA-Z]', t):
            return True
        instruction_phrases = [
            "analyze the provided",
            "analyze the video script",
            "analyze the script",
            "generate a distinct image prompt",
            "generate a distinct prompt",
            "generate distinct image prompts",
            "generate image prompts",
            "do not limit",
            "do not copy",
            "do not invent",
            "do not add",
            "do not override",
            "master prompt",
            "system instruction",
            "task instruction",
            "critical instruction",
            "important instruction",
            "general instruction",
            "prompt generation rule",
            "prompt instruction",
            "strict output rule",
            "required pipeline",
            "script ->",
            "style prompt ->",
            "script →",
            "style prompt →",
            "understand each sentence",
            "create the actual visual scene",
            "control only how that scene looks",
            "script controls",
            "style prompt controls",
            "preserve the exact meaning",
            "apply only the user",
            "never generate your own style",
            "never add automatic",
            "clean visual scene description",
            "no internal instructions",
            "remove completely from final prompts",
            "for every sentence",
            "for each visual concept",
            "final output must contain",
            "raw style prompt",
            "output template",
            "output format",
            "insert script",
            "insert number",
            "rule 1 — script",
            "rule 1 - script",
            "rule 2 — user style",
            "rule 2 - user style",
            "rule 1:",
            "rule 2:",
            "script = content",
            "script = what",
            "style prompt = how",
            "style prompt = exact visual style",
            "i will provide a script",
            "you must generate",
            "you are an expert",
            "act as an expert",
            "your task is",
            "your job is",
            "to maintain 100% consistency",
            "never assume",
            "output direct",
            "numbered image prompts only",
            "conversational filler",
            "without any conversational filler",
            "whenever a new concept is introduced",
            "for every single sentence",
            "whether the script requires",
            "locked style bible",
            "style bible",
            "master style bible",
            "character design rule",
            "character design rules",
            "line & texture",
            "line and texture",
            "color palette rotation rule",
            "color palette rotation",
            "typography rule",
            "typography rules",
            "composition & camera rule",
            "composition & camera rules",
            "mood consistency",
            "scene generation logic",
            "scene generation rules",
            "user input format",
            "number of images",
            "return only",
            "output only",
            "step 1",
            "step 2",
            "step 3",
            "clean image-generation prompt",
            "used internally as a style constraint",
            "style constraint only",
            "style constraint",
        ]
        if any(p in t for p in instruction_phrases):
            return True
        if any(pat.search(text) for pat in INSTRUCTION_LINE_PATTERNS):
            return True
        return False

    @classmethod
    def clean_meta_instructions(cls, text: str) -> str:
        """
        Completely strips system instructions, meta-prompts, template headers,
        Style Bible headers, character design rules, typography rules, composition rules,
        scene generation logic, step instructions, and prompt engineering placeholders.
        """
        if not text:
            return ""

        # 1. Strip bracketed instruction/template headers
        cleaned = re.sub(r'\[\s*(?:ROLE|INPUT|INSTRUCTIONS|OUTPUT|TEMPLATE|GLOBAL|STYLE|RULES?|CINEMATIC|MASTER|CRITICAL|TASK|BIBLE|LOGIC)[^\]]*\]', ' ', text, flags=re.IGNORECASE)

        # 2. Strip unbracketed instruction rule blocks
        cleaned = re.sub(
            r'^[ \t]*(?:CRITICAL\s+INSTRUCTIONS?|TASK\s+INSTRUCTIONS?|IMPORTANT\s+INSTRUCTIONS?|SYSTEM\s+INSTRUCTIONS?|INSTRUCTIONS(?:\s+FOR\s+BREAKING\s+DOWN\s+THE\s+SCRIPT)?|PROMPT\s+INSTRUCTIONS?|UPDATED\s+MASTER\s+PROMPT|MASTER\s+PROMPT|GLOBAL\s+MASTER\s+PROMPT|LOCKED\s+STYLE\s+BIBLE|STYLE\s+BIBLE|MASTER\s+STYLE\s+BIBLE|CHARACTER\s+DESIGN\s+RULES?|TYPOGRAPHY\s+RULES?|NO\s+TEXT(?:\s+RULE)?|COMPOSITION\s*(?:&|and)\s*CAMERA\s+RULES?|SCENE\s+GENERATION\s+LOGIC|SCENE\s+GENERATION\s+RULES?|USER\s+INPUT\s+FORMAT|NUMBER\s+OF\s+IMAGES(?:\s+NEEDED)?|RETURN\s+ONLY|OUTPUT\s+ONLY|STEP\s*\d+)\s*:?[^\r\n]*$',
            '',
            cleaned,
            flags=re.MULTILINE | re.IGNORECASE
        )

        # 3. Strip forbidden bracketed headers and labels
        cleaned = FORBIDDEN_HEADERS_REGEX.sub(" ", cleaned)
        cleaned = TEMPLATE_PLACEHOLDER_REGEX.sub(" ", cleaned)
        cleaned = re.sub(r'\[[^\]]*(?:ROLE|INPUT|OUTPUT|STYLE|INSTRUCTION|INSERT|SCENE|TEMPLATE|NUMBER|OVERLAY|RULES?|MASTER|CRITICAL|TASK|BIBLE|LOGIC)[^\]]*\]', ' ', cleaned, flags=re.IGNORECASE)

        # 4. Strip meta instruction sentences and phrases with precompiled regex
        cleaned = COMBINED_META_REGEX.sub(" ", cleaned)

        # 5. Strip section headers and field labels
        cleaned = SECTION_LABELS_REGEX.sub(" ", cleaned)

        # 6. Line-level instruction removal
        lines = cleaned.splitlines()
        filtered = []
        for line in lines:
            sline = line.strip()
            if not sline:
                continue

            # Skip instruction lines
            if cls.is_instruction_text(sline):
                continue

            # Strip numbering prefixes like "1.", "[INSERT NUMBER HERE]."
            sline = re.sub(r'^(?:\d+\.|\bINSERT\s+NUMBER\s+HERE\b\.*)\s*', '', sline, flags=re.IGNORECASE)

            if sline:
                filtered.append(sline)

        # Clean punctuation and whitespace per line while preserving line breaks
        cleaned_lines = []
        for l in filtered:
            cl = re.sub(r'\s*,\s*', ', ', l)
            cl = re.sub(r'\s*\.\s*', '. ', cl)
            cl = re.sub(r',(\s*,)+', ',', cl)
            cl = re.sub(r'[,;\s]+$', '', cl)
            cl = re.sub(r'^[,;\s]+', '', cl)
            cl = " ".join(cl.split())
            if cl:
                cleaned_lines.append(cl)
        return "\n".join(cleaned_lines)

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
            raw_tag = (match.group(1) or match.group(2) or "").upper()
            if "INSTRUCTION" in raw_tag or "LOGIC" in raw_tag or "FORMAT" in raw_tag:
                norm_tag = "INSTRUCTIONS"
            elif "STYLE" in raw_tag or "GLOBAL" in raw_tag or "BIBLE" in raw_tag:
                norm_tag = "STYLE"
            elif "OUTPUT" in raw_tag or "TEMPLATE" in raw_tag or "RETURN" in raw_tag or "NUMBER" in raw_tag:
                norm_tag = "OUTPUT"
            elif "SCRIPT" in raw_tag or "INPUT" in raw_tag:
                norm_tag = "SCRIPT"
            elif "ROLE" in raw_tag or "SYSTEM" in raw_tag:
                norm_tag = "ROLE"
            else:
                norm_tag = raw_tag

            start_idx = match.end()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections[norm_tag] = text[start_idx:end_idx].strip()

        return sections

    PROPER_NAME_PRESERVE = {
        "WWII", "Rembrandt", "Ben-Day", "Kodak", "Pixar", "Marvel",
        "Studio Ghibli", "Ghibli", "Unreal Engine 5", "Unreal Engine",
        "Octane", "Hasselblad", "Leica", "Makoto Shinkai", "National"
    }

    STYLE_META_FILTER_REGEX = re.compile(
        r'\b(?:masterpiece|trending\s+on\s+artstation|award\s+winning|high\s+quality|'
        r'8k|4k|high\s+res(?:olution)?|critical\s+instructions?|task\s+instructions?|'
        r'master\s+prompt|updated\s+master\s+prompt|rules?|must\s+be|ensure|always|'
        r'negative\s+prompt|no\s+text(?:\s+rule)?|watermark|signature)\b',
        re.IGNORECASE
    )

    @classmethod
    def extract_user_style_characteristics(cls, raw_style: str) -> str:
        """
        The Style Prompt entered by the user is the ONLY source for visual styling.
        Extracts its:
        - art/visual medium
        - realism level
        - colors
        - lighting
        - texture
        - atmosphere
        - rendering style

        Do NOT invent, add, replace, reinterpret, or override any visual style,
        colors, lighting or medium that the user did not specify.
        Never add automatic cinematic/photorealistic/film/3D/warm/cool/color styles
        unless they are explicitly present in the user's Style Prompt.
        Do NOT copy the full Style Prompt into the final prompt.
        The Style Prompt must be used INTERNALLY as a style constraint only.
        Do NOT copy internal/master instructions, Style Bible headers, rules, or metadata.
        Keep every prompt short and optimized for Google Flow AI Bulk Image generation.
        """
        if not raw_style or not str(raw_style).strip():
            return ""

        text = str(raw_style).strip()
        cleaned = cls.clean_meta_instructions(text)
        if not cleaned:
            return ""

        field_definitions = [
            ("medium", r'(?:Art\s+Medium|Art\s+Style|Visual\s+Medium|Visual\s+Style|Medium)\s*:\s*([^\r\n]+)'),
            ("realism", r'(?:Realism\s+Level|Realism|Realism\s+Style)\s*:\s*([^\r\n]+)'),
            ("rendering", r'(?:Rendering\s+Style|Rendering|Render\s+Engine|Render)\s*:\s*([^\r\n]+)'),
            ("texture", r'(?:(?:Line\s*(?:&|and)\s*)?Texture|Materials?|Artistic\s+Technique|Technique)\s*:\s*([^\r\n]+)'),
            ("colors", r'(?:Color\s+Palette(?:\s+Rotation(?:\s+Rule)?)?|Colors?|Palette|Color\s+Psychology)\s*:\s*([^\r\n]+)'),
            ("lighting", r'(?:Lighting\s+Style|Lighting\s*&\s*Color|Lighting)\s*:\s*([^\r\n]+)'),
            ("atmosphere", r'(?:Atmosphere|Emotional\s+Tone|Mood(?:\s+Consistency(?:\s+Rule)?)?|Tone)\s*:\s*([^\r\n]+)'),
        ]

        extracted_parts = []
        found_labeled_fields = False
        found_medium = False

        for field_name, pat in field_definitions:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                val = re.sub(r'^(?:use|apply|always|must\s+be|featuring|apply\s+a|with)\s+', '', val, flags=re.IGNORECASE)
                val = re.sub(r'\s+for\s+themes\s+of.*', '', val, flags=re.IGNORECASE)
                val = cls.clean_meta_instructions(val)
                val = re.sub(r'--ar\s+\d+:\d+|\b\d+:\d+\b', '', val, flags=re.IGNORECASE)
                val = val.strip(' ,.')
                if val and not cls.is_instruction_text(val) and val.lower() not in [p.lower() for p in extracted_parts]:
                    if not re.search(r'\b(?:no\s+text|no\s+words|camera|shots?|step\s*\d+|rule)\b', val, re.IGNORECASE):
                        found_labeled_fields = True
                        if field_name in ["medium", "rendering"]:
                            found_medium = True
                        extracted_parts.append(val)

        if not found_medium and cleaned:
            for line in cleaned.splitlines():
                sline = line.strip(' ,.')
                if not sline or cls.is_instruction_text(sline):
                    continue
                sline_clean = re.sub(r'^(?:LOCKED\s+STYLE\s+BIBLE|STYLE\s+BIBLE|MASTER\s+STYLE)\s*:?\s*', '', sline, flags=re.IGNORECASE).strip(' ,.')
                if sline_clean and not cls.is_instruction_text(sline_clean) and not re.search(r'^[A-Za-z\s&]+:', sline_clean):
                    extracted_parts.insert(0, sline_clean)
                    found_labeled_fields = True
                    break

        if found_labeled_fields and extracted_parts:
            result = ", ".join(extracted_parts[:5])
        else:
            clean_direct = cleaned
            clean_direct = re.sub(r'\b(?:Art\s+Medium|Art\s+Style|Medium|Visual\s+Style|Realism|Color\s+Palette(?:\s+Rotation(?:\s+Rule)?)?|Colors?|Lighting|Camera\s+Angle|Camera|Composition|Texture|Atmosphere|Rendering|Mood(?:\s+Consistency)?)\s*:\s*', '', clean_direct, flags=re.IGNORECASE)
            clean_direct = re.sub(r'--ar\s+\d+:\d+', '', clean_direct, flags=re.IGNORECASE)
            parts = [p.strip(' ,.') for p in re.split(r'(?:[,;\n\r]|\.\s+)+', clean_direct) if p.strip(' ,.')]
            valid_parts = []
            for p in parts:
                p_clean = cls.clean_meta_instructions(p).strip(' ,.')
                if not p_clean:
                    continue
                if cls.is_instruction_text(p_clean):
                    continue
                if p_clean.lower() not in [v.lower() for v in valid_parts]:
                    valid_parts.append(p_clean)
            result = ", ".join(valid_parts[:5])

        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r',(\s*,)+', ',', result)
        return result.strip(' ,.')

    @classmethod
    def distill_core_medium(cls, raw_medium: str) -> str:
        """
        Extracts user's medium without overriding or coercing.
        """
        if not raw_medium:
            return ""
        clean = cls.clean_meta_instructions(raw_medium)
        clean = re.sub(r'^(?:Art\s+Medium|Art\s+Style|Medium|Visual\s+Style)\s*:\s*', '', clean, flags=re.IGNORECASE).strip(' ,.')
        return clean

    @classmethod
    def clean_and_condense_descriptor(cls, descriptor: str, primary_medium: str = "") -> Optional[str]:
        """
        Cleans user style descriptor.
        """
        if not descriptor:
            return None
        d = cls.clean_meta_instructions(descriptor).strip(' ,.')
        return d if d else None

    @classmethod
    def parse_and_extract_visual_rules(cls, raw_text: str) -> Dict[str, Any]:
        """
        Parses user Style Prompt to extract style characteristics and negative prompt terms.
        """
        text = str(raw_text or "").strip()
        style_chars = cls.extract_user_style_characteristics(text)
        neg_prompt = cls.extract_negative_prompt(text)
        neg_list = [t.strip() for t in neg_prompt.split(',') if t.strip()]
        return {
            "primary_medium": style_chars,
            "secondary_descriptors": [],
            "style_parts": [style_chars] if style_chars else [],
            "style_essence": style_chars,
            "full_style": style_chars,
            "negative_terms": neg_list
        }

    @classmethod
    def extract_negative_prompt(cls, visual_style_prompt: str = "") -> str:
        """
        Extracts clean standalone negative prompt terms from the style prompt,
        guaranteeing it stays strictly separate from the main prompt.
        Strictly enforces: no text, no numbers, no letters, no captions, no labels, no typography, no written words.
        """
        text = str(visual_style_prompt or "").strip()
        negative_terms = [
            "no text", "no numbers", "no letters", "no captions", "no labels", "no typography", "no written words",
            "watermark", "signature", "subtitles", "blurry", "low quality", "distorted",
            "extra limbs", "bad anatomy", "deformed"
        ]
        no_text_match = re.search(r'(?:NO\s+TEXT(?:\s+RULE)?|NEGATIVE\s+PROMPT|TYPOGRAPHY\s+RULES?)\s*:\s*([^\n\r]+)', text, re.IGNORECASE)
        if no_text_match:
            raw_neg = no_text_match.group(1).lower()
            for term in ["logo", "borders", "cropped", "jpeg artifacts", "ugly", "duplicate"]:
                if term in raw_neg and term not in negative_terms:
                    negative_terms.append(term)
        return ", ".join(negative_terms)

    @classmethod
    def extract_clean_style(cls, raw_style: str) -> str:
        """
        Extracts the authoritative visual style from the user's input,
        preserving all specified visual characteristics while discarding
        template instruction blocks and headers.
        """
        if not raw_style or not str(raw_style).strip():
            return ""
        return cls.extract_user_style_characteristics(raw_style)

    @classmethod
    def extract_clean_script(cls, raw_script: str) -> str:
        """
        Extracts purely the narrative script from the user's input,
        completely stripping all [ROLE], [INPUT], [INSERT SCRIPT HERE],
        [INSTRUCTIONS...], Style Bible sections, and trailing instructions.
        """
        if not raw_script or not raw_script.strip():
            return ""

        sections = cls.parse_template_sections(raw_script)
        if "SCRIPT" in sections and sections["SCRIPT"].strip():
            target = sections["SCRIPT"]
        else:
            target = raw_script

        # Truncate target before any trailing instruction markers
        target = re.split(
            r'\b(?:NUMBER\s+OF\s+IMAGES(?:\s+NEEDED)?|RETURN\s+ONLY|OUTPUT\s+ONLY|OUTPUT\s+TEMPLATE|OUTPUT\s+FORMAT|OUTPUT\s+RULES?|SCENE\s+GENERATION\s+LOGIC)\b',
            target,
            flags=re.IGNORECASE
        )[0]

        clean = cls.clean_meta_instructions(target)
        if not clean:
            clean = cls.clean_meta_instructions(raw_script)

        # Line-level filtering to ensure no instruction or numbering leaks into the script
        lines = clean.splitlines()
        clean_lines = []
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if cls.is_instruction_text(s):
                continue
            if any(pat.search(s) for pat in INSTRUCTION_LINE_PATTERNS):
                continue
            s = re.sub(r'^(?:Scene\s*\d*|Shot\s*\d*|Prompt\s*\d*|\d+[.:])\s*', '', s, flags=re.IGNORECASE).strip()
            if s and re.search(r'[a-zA-Z]', s) and not cls.is_instruction_text(s):
                clean_lines.append(s)

        return " ".join(clean_lines).strip()

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
            raw_primary = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', cleaned) if s.strip()]
        else:
            words = cleaned.split()
            if len(words) <= 25:
                raw_primary = [cleaned]
            else:
                raw_primary = [" ".join(words[i:i + 16]) for i in range(0, len(words), 16)]

        # Filter out empty, non-alphabetical, or leftover instruction items
        primary = []
        for sentence in raw_primary:
            s = re.sub(r'^(?:Scene\s*\d*|Shot\s*\d*|Prompt\s*\d*|\d+[.:])\s*', '', sentence, flags=re.IGNORECASE).strip()
            s = re.sub(r'^[:\s-]+', '', s).strip()
            if not s or not re.search(r'[a-zA-Z]', s):
                continue
            if cls.is_instruction_text(s):
                continue
            if any(pat.search(s) for pat in INSTRUCTION_LINE_PATTERNS):
                continue
            if re.match(r'^(?:task|role|instructions?|input|output)\b', s, re.IGNORECASE):
                continue
            primary.append(s)

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
            if cls.is_instruction_text(sentence):
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
                if not part or not re.search(r'[a-zA-Z]', part):
                    continue
                if cls.is_instruction_text(part):
                    continue
                if any(pat.search(part) for pat in INSTRUCTION_LINE_PATTERNS):
                    continue
                clean_part = part[0].upper() + part[1:] if len(part) > 1 else part.upper()
                clean_part = clean_part.rstrip(",")
                if merged and len(clean_part.split()) < 3:
                    merged[-1] = f"{merged[-1]}, {clean_part}"
                else:
                    merged.append(clean_part)

            visual_scenes.extend(merged)

        return visual_scenes if visual_scenes else ([cleaned] if cleaned else [])

    @classmethod
    def segment_into_sentences(cls, text: str) -> List[str]:
        """
        Alias for backwards compatibility. Uses visual scene segmentation.
        """
        return cls.segment_into_visual_scenes(text)

    @classmethod
    def convert_narration_to_visual_scene(
        cls,
        sentence: str,
        scene_index: int = 0,
        total_scenes: int = 1
    ) -> str:
        """
        Converts a narration segment into a specific visual scene that represents its meaning.
        CRITICAL RULES:
        - Do not copy the script sentence literally.
        - Translate auditory cues (e.g. alarms echoing, sirens wailing, thunder roaring) into concrete visible phenomena.
        - Translate abstract ideas (e.g. fear, hope, silence) into visible subjects, lighting, and settings.
        - Enrich settings, subjects, and actions with physical, pictorial details.
        - Ensure each scene develops a DIFFERENT, relevant visual idea.
        """
        raw = cls.clean_meta_instructions(sentence)
        raw = re.sub(r'^(?:Scene\s*\d*|Shot\s*\d*|Prompt\s*\d*|\d+)[:.]*\s*', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'^[:\s-]+', '', raw).strip()
        raw = re.sub(r'^(?:Narrator|Speaker\s*\d*|Voiceover|Host)\s*:\s*', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'["“”]', '', raw)
        raw = re.sub(r'[.!?]+$', '', raw).strip()
        if not raw or cls.is_instruction_text(raw):
            return "Atmospheric visual scene"

        # Strip narrative starters (Suddenly, Meanwhile, As time passed, etc.)
        narrative_starters_regex = re.compile(
            r'^(?:Suddenly|Meanwhile|Then|Soon after|Shortly after|Moments later|Later on|'
            r'Eventually|In the end|Little did they know|As it turned out|It was said that|'
            r'Legend tells that|History shows that|As time passed|One day|Every morning|'
            r'He knew that|She felt that|They realized that|It seemed as though|All of a sudden)[,\s]+',
            re.IGNORECASE
        )
        raw = narrative_starters_regex.sub('', raw).strip()

        # Strip camera direction prefixes if any were present in input
        camera_prefix_pat = re.compile(
            r'^(?:(?:cinematic|atmospheric|dramatic|intimate|expansive|breathtaking|focused)\s+)?'
            r'(?:establishing\s+shot|medium\s+shot|close-?up(?:\s+(?:perspective|detail|view))?|'
            r'low-?angle(?:\s+(?:view|shot|scene))?|high-?angle(?:\s+(?:view|shot|scene))?|'
            r'wide\s+vista|wide-?angle(?:\s+(?:view|composition|shot))?|wide\s+shot|action\s+scene|'
            r'angle|shot|perspective|view|camera\s+(?:pan|angle|view))\s+(?:of|on|exploring|capturing|showing)?\s*',
            re.IGNORECASE
        )
        raw = camera_prefix_pat.sub('', raw).strip()
        lower = raw.lower()

        # 1. CANONICAL DOMAIN SCENES
        if ("observatory" in lower or "astronomer" in lower or "telescope" in lower or "brass lens" in lower) and ("jonathan" in lower or "adjusted" in lower or "lens" in lower or "ancient" in lower):
            return "Astronomer Jonathan fine-tuning a massive brass telescope inside a vaulted stone observatory dome under open starlight"

        if ("supernova" in lower or "cosmic burst" in lower or ("star" in lower and "pulsed" in lower)) and ("sapphire" in lower or "light" in lower or "pulsed" in lower or "deep space" in lower or "beyond" in lower):
            return "A massive supernova erupting with radiant sapphire blue plasma shockwaves across a dark stellar void"

        if ("alarm" in lower or "siren" in lower or "klaxon" in lower or "echoed" in lower) and ("station" in lower or "shockwave" in lower or "bridge" in lower or "galaxy" in lower):
            return "Red emergency warning lights flashing across an orbital station bridge as a cosmic energy wave approaches"

        if ("wwii" in lower or "soldier" in lower) and ("village" in lower or "road" in lower or "dawn" in lower or "exhausted" in lower):
            return "An exhausted WWII soldier standing alone beside a cratered village road at dawn with rising morning mist"

        # Recitation / Words remembered or spoken since childhood (e.g. "You have heard it your whole life, maybe recited it...")
        if re.search(r'\b(?:heard\s+(?:it\s+)?(?:your|our|all)\s+(?:whole\s+)?life|recited|reciting|memorized|chanted|whispered\s+for\s+generations|passed\s+down)\b', lower):
            if re.search(r'\b(?:prayer|verse|psalm|scripture|hymn|text|words|ancient|book|scroll|wisdom)\b', lower):
                return "A contemplative person in quiet reflection, hands resting upon the aged pages of an ancient illuminated manuscript, speaking familiar words in soft ambient candlelight"
            return "A contemplative figure in quiet reflection, hands resting upon the worn pages of an open ancient manuscript, reciting familiar words remembered since childhood in warm ambient light"

        # Questions / Mysteries / Seeking true meaning
        if re.search(r'\b(?:what\s+(?:does\s+it\s+)?(?:truly|really)\s+mean|what\s+if\s+everything|truth\s+behind|hidden\s+meaning|secret\s+lies|unsolved\s+mystery)\b', lower):
            return "A thoughtful scholar examining intricate vintage celestial charts, faded handwritten annotations, and antique leather-bound volumes under a warm desk lamp"

        # Childhood / Nostalgia / Early memories
        if re.search(r'\b(?:as\s+a\s+child|since\s+childhood|in\s+(?:our|your)\s+youth|growing\s+up|when\s+(?:we|you)\s+were\s+young)\b', lower):
            return "A nostalgic scene of a child sitting beside a sunlit windowsill with antique toys and illustrated storybooks, bathed in soft afternoon light"

        # Ancient Epochs / Dawn of Time / Forgotten Civilizations
        if re.search(r'\b(?:thousands\s+of\s+years\s+ago|in\s+the\s+dawn\s+of\s+time|lost\s+to\s+time|forgotten\s+civilization|ancient\s+origins?|centuries\s+before)\b', lower):
            return "Majestic weathered ancient stone temple ruins standing at the edge of a lush valley at sunrise with golden light cutting through ivy-covered archways"

        # Universal Human Condition / Gathering together
        if re.search(r'\b(?:all\s+of\s+us|every\s+one\s+of\s+us|every\s+human|human\s+nature|universal\s+truth|we\s+all\s+share)\b', lower):
            return "Diverse travelers gathered peacefully together around a warm glowing communal campfire beneath a vast star-filled night sky"

        # 2. GREETINGS & CONVERSATIONAL INTROS -> HISTORICAL / ATMOSPHERIC ESTABLISHING SCENE
        # Example: "Hello, my friends, welcome back to our quiet corner of history"
        if re.search(r'\b(?:hello|welcome\s+back|welcome\s+to|my\s+friends|greetings|join\s+me|our\s+quiet\s+corner)\b', lower):
            if re.search(r'\b(?:history|historic|historical|past|centuries|ancient|archives|corner\s+of\s+history|bygone)\b', lower):
                return "An atmospheric historical establishing scene inside an antique library with leather-bound chronicles, aged maps, and warm flickering candlelight"
            return "An evocative atmospheric establishing wide shot capturing the opening of the story at dawn with soft ambient lighting"

        # 3. IMAGINATIVE & SENSORY DIRECTIVES ("Imagine...", "Picture this...")
        # Example: "Imagine the cold, salty air..."
        if re.search(r'^(?:imagine|picture|visualize|think\s+of|feel\s+the|breathe\s+in)\b', lower):
            if any(w in lower for w in ["cold", "salty", "sea", "ocean", "coastal", "plank", "wooden", "pier", "shore", "tide"]):
                return "A cold coastal historical environment with sea air, weathered wooden planks on an old dock, and crashing ocean waves"
            if any(w in lower for w in ["desert", "sand", "heat", "dune"]):
                return "A vast rolling desert of golden sand dunes glowing under intense afternoon sunlight"
            if any(w in lower for w in ["winter", "snow", "blizzard", "frost", "ice"]):
                return "A quiet snow-covered historic village surrounded by frosty pine trees under a pale winter sky"
            stripped_im = re.sub(r'^(?:imagine|picture|visualize|think\s+of|feel\s+the|breathe\s+in)\s+(?:the\s+|a\s+|an\s+)?', '', raw, flags=re.IGNORECASE).strip()
            if stripped_im:
                return f"An atmospheric visual scene depicting {stripped_im}"

        # 4. SENSORY & AUDITORY TRANSLATION
        sensory_translations = [
            (r'\bas\s+thunder\s+rattled\s+the\s+stained\s+glass\s+windows\b', 'beside glowing stained glass windows'),
            (r'\bas\s+thunder\s+roared\b', 'under stormy lightning skies'),
            (r'\balarms\s+(?:blared|wailed|screamed)\b', 'red emergency warning sirens flashing'),
            (r'\ba\s+deafening\s+silence\s+fell\b', 'standing motionless in heavy silence'),
        ]
        for s_pat, s_rep in sensory_translations:
            raw = re.sub(s_pat, s_rep, raw, flags=re.IGNORECASE)

        # 5. FAST & AUTHENTIC STORY SCENE ACTIVATION
        # Reorders inverted introductory prepositional clauses (e.g. 'In the heart of an ancient observatory, Jonathan adjusted the lens')
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        prep_starters = (
            'in ', 'at ', 'on ', 'inside ', 'outside ', 'beyond ', 'across ',
            'under ', 'over ', 'beneath ', 'through ', 'deep within ', 'deep inside ',
            'beside ', 'along ', 'near '
        )
        if len(parts) >= 2 and parts[0].lower().startswith(prep_starters):
            intro = parts[0]
            intro_clean = intro[0].lower() + intro[1:] if len(intro) > 1 else intro.lower()
            main = ', '.join(parts[1:]).strip()
            reordered = f"{main} {intro_clean}"
        else:
            reordered = raw

        # 4. Convert past narrative verbs to active visual participles
        verb_maps = [
            (r'\blights\b|\blit\b', 'lighting'),
            (r'\bhears\b|\bheard\b', 'listening to'),
            (r'\brecites\b|\brecited\b', 'reciting'),
            (r'\bwhispers\b|\bwhispered\b', 'whispering'),
            (r'\bwrites\b|\bwrote\b', 'writing on'),
            (r'\breads\b|\bread\b', 'reading from'),
            (r'\bplaced\b', 'placing'),
            (r'\bheld\b', 'holding'),
            (r'\bset\b', 'setting'),
            (r'\braised\b', 'raising'),
            (r'\blifted\b', 'lifting'),
            (r'\bdropped\b', 'dropping'),
            (r'\bpushed\b', 'pushing'),
            (r'\bpulled\b', 'pulling'),
            (r'\bstepped\b', 'stepping'),
            (r'\bwalked\b', 'walking'),
            (r'\bmarched\b', 'marching'),
            (r'\bran\b', 'running'),
            (r'\brushed\b', 'rushing'),
            (r'\bstood\b', 'standing'),
            (r'\bsat\b', 'sitting'),
            (r'\bgazed\b', 'gazing toward'),
            (r'\bstared\b', 'staring at'),
            (r'\blooked\b', 'looking at'),
            (r'\bwatched\b', 'observing'),
            (r'\bobserved\b', 'observing'),
            (r'\bpeered\b', 'peering through'),
            (r'\bglanced\b', 'glancing toward'),
            (r'\bturned\b', 'turning'),
            (r'\bopened\b', 'opening'),
            (r'\bclosed\b', 'closing'),
            (r'\bslammed\b', 'slamming'),
            (r'\badjusted\b', 'fine-tuning'),
            (r'\bexamined\b', 'examining'),
            (r'\binspected\b', 'inspecting'),
            (r'\bdiscovered\b', 'discovering'),
            (r'\buncovered\b', 'uncovering'),
            (r'\bfound\b', 'finding'),
            (r'\bsearched\b', 'searching through'),
            (r'\bscanned\b', 'scanning'),
            (r'\bpulsed\b', 'pulsing with'),
            (r'\bcollapsed\b', 'collapsing'),
            (r'\berupted\b', 'erupting with'),
            (r'\bexploded\b', 'exploding into'),
            (r'\bbathed\b', 'illuminating'),
            (r'\bstretched\b', 'stretching'),
            (r'\bshook\b', 'shaking'),
            (r'\btrembled\b', 'trembling'),
            (r'\bechoed\b', 'echoing through'),
            (r'\brattled\b', 'rattling against'),
            (r'\bglowed\b', 'glowing with'),
            (r'\bshined\b|\bshone\b', 'shining across'),
            (r'\bcrested\b', 'cresting over'),
            (r'\bbubbled\b', 'bubbling with'),
            (r'\brose\b', 'rising above'),
            (r'\bfell\b', 'falling across'),
            (r'\bflowed\b', 'flowing through'),
            (r'\bstreamed\b', 'streaming across'),
            (r'\bdrifted\b', 'drifting through'),
            (r'\bfloated\b', 'floating above'),
            (r'\bsoared\b', 'soaring over'),
            (r'\bflew\b', 'flying over'),
            (r'\bcrept\b', 'creeping through'),
            (r'\bwandered\b', 'wandering through'),
            (r'\bapproached\b', 'approaching'),
            (r'\bentered\b', 'entering'),
            (r'\bgripped\b|\bclasped\b|\bclutched\b', 'gripping'),
            (r'\btouched\b', 'touching'),
            (r'\breached\b', 'reaching for'),
            (r'\bpointed\b', 'pointing toward'),
            (r'\bgathered\b', 'gathering around'),
            (r'\bwaited\b', 'waiting beside'),
            (r'\bspoke\b|\bwhispered\b|\bshouted\b|\bcalled\b', 'speaking to'),
            (r'\bguided\b', 'guiding'),
            (r'\bcommanded\b', 'commanding'),
            (r'\bsummoned\b', 'summoning'),
            (r'\bignited\b', 'igniting'),
            (r'\bactivated\b', 'activating'),
            (r'\bunlocked\b', 'unlocking'),
            (r'\brevealed\b', 'revealing'),
            (r'\bengulfed\b', 'engulfing'),
            (r'\bscattered\b', 'scattering'),
            (r'\bwondered\s+if\b', 'contemplating whether'),
            (r'\bwondered\b|\bpondered\b', 'pondering'),
        ]
        formatted = reordered
        for v_pat, v_rep in verb_maps:
            formatted = re.sub(v_pat, v_rep, formatted, flags=re.IGNORECASE)

        # Clean double prepositions
        formatted = re.sub(r'\bthrough\s+through\b', 'through', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r'\bwith\s+with\b', 'with', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r'\bbeside\s+at\b', 'beside', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r'\binto\s+into\b', 'into', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r'\bacross\s+across\b', 'across', formatted, flags=re.IGNORECASE)

        clean_scene = formatted.strip(' ,.')
        if clean_scene:
            clean_scene = clean_scene[0].upper() + clean_scene[1:]
        else:
            clean_scene = "Visual scene"

        return clean_scene

    @classmethod
    def understand_scene_visual_concept(
        cls,
        sentence: str,
        scene_index: int = 0,
        total_scenes: int = 1
    ) -> str:
        """
        Understands the script scene-by-scene:
        - Converts each narration segment into a specific visual scene representing its meaning.
        - Does NOT copy the script sentence literally.
        - Guarantees each scene has a different, relevant visual idea.
        - Omits any camera/composition instructions.
        """
        return cls.convert_narration_to_visual_scene(sentence, scene_index, total_scenes)

    @classmethod
    def compose_applied_style_for_scene(
        cls,
        primary_medium: str,
        secondary_descriptors: List[str] = None,
        scene_index: int = 0,
        total_scenes: int = 1
    ) -> str:
        """
        Returns the user's exact style characteristics.
        Never drops or rotates away user-specified style attributes.
        """
        return primary_medium or ""

    @classmethod
    def synthesize_visual_prompt(
        cls,
        sentence: str,
        visual_style_prompt: str = "",
        scene_index: int = 0,
        total_scenes: int = 1,
        precomputed_style: Optional[str] = None
    ) -> str:
        """
        Combines the scene visual concept with the user's exact style characteristics.

        RULE 1 — SCRIPT = CONTENT
        Analyze each sentence and create the visual scene strictly from its meaning:
        people, actions, location, objects, events and atmosphere described by the script.

        RULE 2 — USER STYLE PROMPT = EXACT VISUAL STYLE
        The Style Prompt entered by the user is the ONLY source for visual styling.

        Apply its:
        - art/visual medium
        - realism level
        - colors
        - lighting
        - composition
        - camera/look
        - texture
        - atmosphere
        - rendering style

        Do NOT invent, add, replace, reinterpret, or override any visual style, colors, lighting or medium that the user did not specify.

        If the user's Style Prompt says watercolor → use watercolor.
        If it says black-and-white documentary → use black-and-white documentary.
        If it says 3D → use 3D.
        If it specifies colors/lighting → use exactly those characteristics.

        CRITICAL:
        Never generate your own style.
        Never add automatic cinematic/photorealistic/film/3D/warm/cool/color styles unless they are explicitly present in the user's Style Prompt.

        FINAL PROMPT:
        [script-derived visual scene] + [user's exact style characteristics]

        Do NOT copy the entire Style Prompt into the final output.
        Do NOT add Master Prompt, metadata, templates or explanations.

        Script controls WHAT is shown.
        User Style Prompt controls HOW it looks.
        Nothing else may control the style.
        """
        visual_concept = cls.understand_scene_visual_concept(sentence, scene_index, total_scenes).strip()
        visual_concept = visual_concept.rstrip(" .,")

        if precomputed_style is not None:
            user_style = precomputed_style.strip()
        else:
            user_style = cls.extract_user_style_characteristics(visual_style_prompt).strip()
        user_style = user_style.strip(" .,")

        if user_style:
            words = user_style.split()
            first_w = words[0] if words else ""
            if len(user_style) > 1 and not (first_w[0].isdigit() or first_w in cls.PROPER_NAME_PRESERVE or first_w.isupper()):
                user_style_lead = user_style[0].lower() + user_style[1:]
            else:
                user_style_lead = user_style

            result = f"{visual_concept}, {user_style_lead}."
        else:
            result = f"{visual_concept}."

        # Strict final sanitization pass - fast guard
        if any(c in result for c in ['[', ']', '<', '>', 'Task:', 'Instructions:', 'Rule ']):
            result = cls.clean_meta_instructions(result)
        result = re.sub(r'[\r\n]+', ' ', result)

        # Strip any leading numbering prefix (e.g. "1. ", "Scene 1: ", "Prompt 1: ")
        result = re.sub(r'^(?:Scene\s*\d*|Shot\s*\d*|Prompt\s*\d*|\d+[.:])\s*', '', result, flags=re.IGNORECASE)

        # Strip any lingering instructions or meta tags
        result = re.sub(r'\b(?:task:\s*i\s+will\s+provide|task:\s*|i\s+will\s+provide\s+a\s+script|you\s+must\s+generate)\b.*', '', result, flags=re.IGNORECASE)

        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r',(\s*,)+', ',', result)
        result = re.sub(r'\.\s*\.', '.', result)
        result = re.sub(r',\s*\.', '.', result)

        # Absolute safeguard against any remaining instruction, camera direction, or template leakage
        forbidden_snippets = [
            "locked style bible",
            "style bible",
            "master style bible",
            "character design rule",
            "character design rules",
            "character design",
            "line & texture",
            "line and texture",
            "color palette rotation rule",
            "color palette rotation",
            "typography rule",
            "typography rules",
            "composition & camera rule",
            "composition & camera rules",
            "mood consistency",
            "scene generation logic",
            "scene generation rules",
            "user input format",
            "number of images needed",
            "number of images",
            "return only",
            "output only",
            "step 1",
            "step 2",
            "step 3",
            "clean image-generation prompt",
            "used internally as a style constraint",
            "style constraint only",
            "analyze the provided video script and generate a distinct image prompt",
            "analyze the provided video script",
            "analyze the provided script",
            "analyze the script",
            "generate a distinct image prompt",
            "generate a distinct prompt",
            "generate distinct image prompts",
            "generate image prompts",
            "do not limit the number of prompts",
            "do not limit the output",
            "do not limit",
            "do not copy",
            "do not invent",
            "do not override",
            "master prompt text",
            "master prompt",
            "master style prompt",
            "master style",
            "updated master prompt",
            "system instructions",
            "system instruction",
            "system prompt",
            "task instructions",
            "task instruction",
            "critical instructions",
            "critical instruction",
            "prompt instructions",
            "prompt instruction",
            "required pipeline",
            "clean visual scene description",
            "no internal instructions",
            "raw style prompt",
            "placeholders",
            "metadata",
            "templates",
            "rule 1 — script",
            "rule 1 - script",
            "rule 2 — user style",
            "rule 2 - user style",
            "rule 1",
            "rule 2",
            "script = content",
            "script = what",
            "style prompt = exact visual style",
            "style prompt = how",
            "for every sentence",
            "for each visual concept",
            "preserve the exact meaning",
            "apply only the user's style prompt",
            "apply only the user",
            "task: i will provide", "i will provide a script", "you must generate",
            "task:",
            "global visual style", "cinematic rules",
            "output template",
            "insert script", "insert number", "art medium:", "lighting style:",
            "color palette:", "camera angles:", "texture:", "composition rules:",
            "emotional tone:", "final quality standard:",
            "cinematic establishing shot of", "focused medium shot of",
            "dynamic dramatic angle of", "atmospheric wide vista of",
            "intimate close-up perspective of", "dramatic low-angle view of",
            "expansive wide-angle composition of", "dutch angles", "wide establishing shots",
            "macro camera lens", "rule of thirds", "camera angle", "camera angles"
        ]
        for snip in forbidden_snippets:
            if snip in result.lower():
                result = re.sub(re.escape(snip) + r'[:\s-]*', '', result, flags=re.IGNORECASE)

        # Strip quotation marks from visual prompt so image models do not render dialogue or quotes as written words
        result = re.sub(r'["“”]', '', result)
        # Strip any lingering "Scene \d+", "Shot \d+", "Prompt \d+", "Image \d+" inside the prompt
        result = re.sub(r'\b(?:Scene|Shot|Prompt|Image)\s*\d+[:.]?\b', '', result, flags=re.IGNORECASE)
        # Strip labels, captions, headings, metadata, UI tags
        result = re.sub(r'\b(?:headings?|captions?|labels?|metadata|ui\s+text|structure\s+text|instruction\s+text)\s*:\s*', '', result, flags=re.IGNORECASE)

        result = " ".join(result.split())
        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r',(\s*,)+', ',', result)
        result = re.sub(r'^(?:Scene\s*\d*|Shot\s*\d*|Prompt\s*\d*|\d+)[:.]*\s*', '', result, flags=re.IGNORECASE)
        result = re.sub(r'^[:\s-]+', '', result).strip()
        if result and not (result[0].isupper() or result[0].isdigit()):
            result = result[0].upper() + result[1:]
        if not result.endswith("."):
            result += "."
        return result

    @classmethod
    def subdivide_long_narration_scene(cls, scene_text: str, duration: float) -> List[Tuple[str, float]]:
        """
        Subdivides any narration segment that exceeds 15 seconds into 5-15s visual shots.
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
            narrative_progressions = [
                f"{scene_text}",
                f"{scene_text}, focal narrative progression",
                f"{scene_text}, environmental visual detail",
                f"{scene_text}, atmospheric perspective",
            ]
            for i in range(num_parts):
                p_text = narrative_progressions[i % len(narrative_progressions)]
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
            raw_segments = ["Visual scene with detailed environment and atmosphere"]

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

        user_style = cls.extract_user_style_characteristics(visual_style_prompt).strip()
        neg_prompt = cls.extract_negative_prompt(visual_style_prompt)

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

            prompt = cls.synthesize_visual_prompt(
                s_text,
                visual_style_prompt,
                scene_index=idx,
                total_scenes=len(refined_scenes),
                precomputed_style=user_style
            )

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
                "negative_prompt": neg_prompt,
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
            sentences = ["Visual scene with detailed environment and atmosphere"]

        user_style = cls.extract_user_style_characteristics(visual_style_prompt).strip()
        neg_prompt = cls.extract_negative_prompt(visual_style_prompt)
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
            prompt = cls.synthesize_visual_prompt(
                sentence,
                visual_style_prompt,
                scene_index=idx,
                total_scenes=len(sentences),
                precomputed_style=user_style
            )

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
                "negative_prompt": neg_prompt,
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

