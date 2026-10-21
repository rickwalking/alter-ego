"""Carousel defaults for GrokBot topics.

Simple-words limits, rejection reasons, the stop words ignored when a brief
is matched against its title, and the image-guidance templates. See
``docs/architecture/grokbot-autopilot.md`` §5.3.

Audience and niche are 1-3 words and the brief is short. The API accepts any short style
string; the domain rejects an unsupported one per topic (``image_style_unsupported``)
instead of failing the batch. The stop words are English and Portuguese because the
scout writes either. The fallback image guidance, used when the scout sends none, fills
``{niche}`` from the proposal and keeps the background line theme-specific.
"""

SIMPLE_WORDS_MIN = 1
SIMPLE_WORDS_MAX = 3
SIMPLE_BRIEF_MAX_CHARS = 600
IMAGE_GUIDANCE_MAX_CHARS = 400
IMAGE_STYLE_MAX_CHARS = 32
IMAGE_STYLE_INPUT_MAX_CHARS = 40

REASON_AUDIENCE_NOT_SIMPLE = "audience_not_simple"
REASON_NICHE_NOT_SIMPLE = "niche_not_simple"
REASON_BRIEF_NOT_SIMPLE = "brief_not_simple"
REASON_BRIEF_OFF_THEME = "brief_off_theme"
REASON_IMAGE_STYLE_UNSUPPORTED = "image_style_unsupported"

BRIEF_STOP_WORDS: frozenset[str] = frozenset({
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "its",
    "new",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "why",
    "with",
    "you",
    "your",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "um",
    "uma",
})

GUIDANCE_NEO_ANIME = (
    "Futuristic anime in the style of Akira, Ghost in the Shell and "
    "Neon Genesis Evangelion."
)
GUIDANCE_STYLE_NEUTRAL = "Clean visuals that follow the chosen image style."
GUIDANCE_BACKGROUND_TEMPLATE = "Background: {niche}-themed setting."
GUIDANCE_JOIN = " "

LABEL_AUDIENCE = "Audience"
LABEL_NICHE = "Niche"
LABEL_STYLE = "Style"
PROFILE_LINE_TEMPLATE = (
    "{audience_label}: {audience} · {niche_label}: {niche} · {style_label}: {style}"
)
PROFILE_SEPARATOR = "\n\n"
