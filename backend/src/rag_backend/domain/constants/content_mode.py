"""Carousel content modes and the "Ponto de Vista" inputs (AE-0373, ADR-0021).

``news_analysis`` ("Radar IA") is the default and the meaning of every row whose
``content_mode`` is NULL. ``pov`` ("Ponto de Vista") carries the owner's thesis:
the model may sharpen it, never invent it.
"""

from __future__ import annotations

CONTENT_MODE_NEWS_ANALYSIS = "news_analysis"
CONTENT_MODE_POV = "pov"
DEFAULT_CONTENT_MODE = CONTENT_MODE_NEWS_ANALYSIS
CONTENT_MODES: frozenset[str] = frozenset({
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
})

# POV formats (growth plan 16.3 B): each picks the outline narrative and the
# layout of the point slides.
POV_FORMAT_OPINION = "opiniao"
POV_FORMAT_HOW_I = "como_eu_faco"
POV_FORMAT_MISTAKES = "erros_e_mitos"
POV_FORMAT_COMPARISON = "comparacao"
DEFAULT_POV_FORMAT = POV_FORMAT_OPINION
POV_FORMATS: frozenset[str] = frozenset({
    POV_FORMAT_OPINION,
    POV_FORMAT_HOW_I,
    POV_FORMAT_MISTAKES,
    POV_FORMAT_COMPARISON,
})

# Field limits (growth plan 16.3 A).
POV_THESIS_MAX_CHARS = 280
POV_PERSONAL_PROOF_MAX_CHARS = 500
POV_FORMAT_MAX_CHARS = 30
CONTENT_MODE_MAX_CHARS = 20
CTA_GOAL_MAX_CHARS = 20
HOOK_TEXT_COLUMN_CHARS = 120
HOOK_TEXT_MAX_CHARS = 60
HOOK_MAX_WORDS = 10

# Slide counts: POV 8-10 (default 9); Radar IA 7, or 8 with the optional twist.
POV_SLIDE_COUNT_MIN = 8
POV_SLIDE_COUNT_MAX = 10
POV_SLIDE_COUNT_DEFAULT = 9
NEWS_SLIDE_COUNT_MIN = 7
NEWS_SLIDE_COUNT_MAX = 8

ERR_POV_THESIS_REQUIRED = "pov_thesis is required when content_mode is 'pov'"
ERR_POV_FORMAT_UNKNOWN = "pov_format must be one of {}, got {!r}"
ERR_SLIDE_COUNT_RANGE = "slide_count must be between {} and {} for {}, got {}"
ERR_POV_FIELDS_ON_NEWS = "{} is only allowed when content_mode is 'pov'"
ERR_CONTENT_MODE_UNKNOWN = "content_mode must be one of {}, got {!r}"
ERR_CTA_GOAL_UNKNOWN = "cta_goal must be one of {}, got {!r}"
ERR_HOOK_BLANK = "hook_text must not be blank"
ERR_HOOK_TOO_MANY_WORDS = "hook_text must have at most {} words"
ERR_HOOK_NOT_SUPPORTED = "hook_not_supported_for_this_carousel"
# PR #106 review: slide 1 of a POV deck is the owner's photo, never optional.
ERR_POV_HOOK_PHOTO_REQUIRED = (
    "hook_asset_id is required when content_mode is 'pov': "
    "choose the slide-1 photo (role hook) from your photo library"
)
ERR_HOOK_PHOTO_MISSING = "hook_photo_missing"
ERR_HOOK_PHOTO_UNREADABLE = "hook_photo_unreadable"

__all__ = [
    "CONTENT_MODES",
    "CONTENT_MODE_MAX_CHARS",
    "CONTENT_MODE_NEWS_ANALYSIS",
    "CONTENT_MODE_POV",
    "CTA_GOAL_MAX_CHARS",
    "DEFAULT_CONTENT_MODE",
    "DEFAULT_POV_FORMAT",
    "ERR_CONTENT_MODE_UNKNOWN",
    "ERR_CTA_GOAL_UNKNOWN",
    "ERR_HOOK_BLANK",
    "ERR_HOOK_NOT_SUPPORTED",
    "ERR_HOOK_PHOTO_MISSING",
    "ERR_HOOK_PHOTO_UNREADABLE",
    "ERR_HOOK_TOO_MANY_WORDS",
    "ERR_POV_FIELDS_ON_NEWS",
    "ERR_POV_FORMAT_UNKNOWN",
    "ERR_POV_HOOK_PHOTO_REQUIRED",
    "ERR_POV_THESIS_REQUIRED",
    "ERR_SLIDE_COUNT_RANGE",
    "HOOK_MAX_WORDS",
    "HOOK_TEXT_COLUMN_CHARS",
    "HOOK_TEXT_MAX_CHARS",
    "NEWS_SLIDE_COUNT_MAX",
    "NEWS_SLIDE_COUNT_MIN",
    "POV_FORMATS",
    "POV_FORMAT_COMPARISON",
    "POV_FORMAT_HOW_I",
    "POV_FORMAT_MAX_CHARS",
    "POV_FORMAT_MISTAKES",
    "POV_FORMAT_OPINION",
    "POV_PERSONAL_PROOF_MAX_CHARS",
    "POV_SLIDE_COUNT_DEFAULT",
    "POV_SLIDE_COUNT_MAX",
    "POV_SLIDE_COUNT_MIN",
    "POV_THESIS_MAX_CHARS",
]
