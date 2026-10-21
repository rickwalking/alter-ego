"""Constants for the owner "Fix issues" deterministic content repair.

The review message lists at most ``AUTOFIX_MAX_ISSUE_LINES`` issue lines. Known proper
nouns are always restored on top of the carousel's own vocabulary and the policy's list;
words that are also common Portuguese words ("Meta" = goal) are deliberately absent. An
all-caps token up to ``ACRONYM_MAX_LENGTH`` is an acronym ("API"), longer is emphasis. A
research title with at least ``TITLE_CASE_SHARE`` capitalized words is Title Case, so
only its distinctive tokens (inner capitals, digits) are trusted. Portuguese markers are
words that look capitalized at a heading start but are never proper nouns (lowercase,
compared after casefold); Portuguese is detected from at least 2 marker words (more than
English markers), or 1 marker plus an accented letter in a text of at least 3 words. The
EN re-translation is the only LLM call of the fix and is bounded.
"""

from __future__ import annotations

AUTOFIX_STATUS_FIXED = "fixed"
AUTOFIX_STATUS_NOTHING_TO_FIX = "nothing_to_fix"
AUTOFIX_STATUS_CONFLICT = "conflict"

AUTOFIX_MAX_ISSUE_LINES = 5
ISSUE_LINE_MORE = "+{count} more issues"
ISSUE_LINE_SLIDE = "Slide {slide}: {text}"
ISSUE_LINE_SLIDE_EN = "Slide {slide} EN: {text}"
ISSUE_LINE_CAROUSEL = "Carousel: {text}"
ISSUE_LINE_RENDER_FAILED = "Carousel: re-render failed ({detail})"

ISSUE_TEXT_HEADING_LOWERCASE = "heading starts lowercase"
ISSUE_TEXT_BODY_LOWERCASE = "body starts lowercase"
ISSUE_TEXT_ITEM_LOWERCASE = "{item} text starts lowercase"
ISSUE_TEXT_BODY_EMPTY = "no body or features"
ISSUE_TEXT_CLOSING_ACTIONS = "fewer than 3 actions"
ISSUE_TEXT_SUMMARY_POINTS = "fewer than 3 summary points"
ISSUE_TEXT_NOT_TRANSLATED = "not translated"
ISSUE_TEXT_MARKUP = "broken bold markup"
ISSUE_TEXT_PROPER_NOUN = "proper noun lowercase ({noun})"

ITEM_LABELS: dict[str, str] = {
    "features": "feature",
    "summary_points": "summary point",
    "actions": "action",
}

KNOWN_PROPER_NOUNS: tuple[str, ...] = (
    "Brasil",
    "Google",
    "OpenAI",
    "Anthropic",
    "ChatGPT",
    "GitHub",
    "LinkedIn",
    "Instagram",
    "Python",
    "JavaScript",
    "TypeScript",
    "Microsoft",
    "Nvidia",
    "Linux",
    "Android",
)

VOCABULARY_MIN_TOKEN_LENGTH = 3
ACRONYM_MAX_LENGTH = 5
TITLE_CASE_SHARE = 0.6
TITLE_CASE_MIN_WORD_LENGTH = 4

PORTUGUESE_MARKERS: frozenset[str] = frozenset({
    "de",
    "da",
    "dos",
    "das",
    "que",
    "não",
    "para",
    "com",
    "uma",
    "os",
    "em",
    "na",
    "nos",
    "nas",
    "é",
    "são",
    "mais",
    "seu",
    "sua",
    "seus",
    "suas",
    "pelo",
    "pela",
    "também",
    "como",
    "mas",
    "ou",
    "isso",
    "este",
    "esta",
    "esse",
    "essa",
    "ao",
    "aos",
    "à",
    "às",
    "quando",
    "porque",
    "sem",
    "sobre",
    "entre",
    "muito",
    "já",
    "ainda",
    "agora",
    "você",
    "vocês",
})
ENGLISH_MARKERS: frozenset[str] = frozenset({
    "the",
    "and",
    "of",
    "to",
    "is",
    "are",
    "with",
    "for",
    "that",
    "this",
    "it",
    "in",
    "on",
    "your",
    "you",
    "now",
    "from",
    "by",
    "an",
    "be",
    "can",
    "will",
    "than",
    "how",
    "what",
    "why",
})
PORTUGUESE_ACCENTS = "ãõçâêôáéíóúà"
PORTUGUESE_MIN_MARKERS = 2
PORTUGUESE_MIN_WORDS_WITH_ACCENT = 3
UNTRANSLATED_MIN_CHARS = 12

FILL_MIN_ITEMS = 3
FILL_MAX_ITEMS = 4
FEATURE_TITLE_MAX_CHARS = 32
FEATURE_BODY_MAX_CHARS = 100
SUMMARY_TITLE_MAX_CHARS = 36
SUMMARY_BODY_MAX_CHARS = 90
CLOSING_ACTION_TITLE_MAX_CHARS = 30
CLOSING_ACTION_BODY_MAX_CHARS = 90
KEY_POINT_SEPARATORS: tuple[str, ...] = (": ", " \u2013 ", " \u2014 ", " - ")

AUTOFIX_TRANSLATE_ATTEMPTS = 2
AUTOFIX_TRANSLATE_TIMEOUT_SECONDS = 90.0
AUTOFIX_PROMPT_DOMAIN = "carousel_autofix"
AUTOFIX_PROMPT_NAME = "en_retranslate"
AUTOFIX_PROMPT_VERSION = "v1"
AUTOFIX_JSON_TRANSLATIONS_KEY = "translations"
AUTOFIX_JSON_ID_KEY = "id"
AUTOFIX_JSON_TEXT_KEY = "text"
AUTOFIX_TARGET_ID = "{slide}:{path}"

LOG_AUTOFIX_APPLIED = "carousel_owner_autofix_applied"
LOG_AUTOFIX_NOOP = "carousel_owner_autofix_noop"
LOG_AUTOFIX_CONFLICT = "carousel_owner_autofix_conflict"
LOG_AUTOFIX_TRANSLATE_FAILED = "carousel_owner_autofix_translate_failed"
LOG_AUTOFIX_RENDER_FAILED = "carousel_owner_autofix_render_failed"
LOG_AUTOFIX_GATE_REPAIRED = "carousel_gate_autofix_applied"
LOG_AUTOFIX_GATE_NOOP = "carousel_gate_autofix_noop"
