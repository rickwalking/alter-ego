"""Limits and contract strings of "create a palette with AI".

A fast-queue LLM call turns the owner's description into up to
``PALETTE_CANDIDATE_COUNT`` candidates; ``GENERATION_ATTEMPTS`` allows a second
call when the first answer has fewer valid ones. ``WCAG_AA_TEXT_CONTRAST`` is the AA
ratio for normal text; the slide ink colours are the template's own (dark ink on
a light background, white on a dark one), so the check matches what renders.
A failing colour is mixed towards black or white in ``CONTRAST_REPAIR_STEP``
increments until it passes.
"""

from __future__ import annotations

PALETTE_CANDIDATE_COUNT: int = 3
DESCRIPTION_MIN_LEN: int = 3
DESCRIPTION_MAX_LEN: int = 300

WCAG_AA_TEXT_CONTRAST: float = 4.5
CONTRAST_REPAIR_STEP: float = 0.05
CONTRAST_DECIMALS: int = 2
SLIDE_INK_ON_LIGHT: str = "#16181d"
SLIDE_INK_ON_DARK: str = "#ffffff"
MIX_TARGET_BLACK: str = "#000000"
MIX_TARGET_WHITE: str = "#ffffff"

GENERATION_TEMPERATURE: float = 0.8
GENERATION_MAX_TOKENS: int = 2000
GENERATION_TIMEOUT_SECONDS: float = 90.0
GENERATION_ATTEMPTS: int = 2

KEY_CANDIDATES: str = "candidates"
KEY_NAME: str = "name"
KEY_PRIMARY: str = "primary"
KEY_ACCENT: str = "accent"
KEY_BACKGROUND: str = "background"
KEY_KEYWORDS: str = "keywords"

PROMPT_DOMAIN_PALETTE: str = "palette"
PROMPT_PALETTE_GENERATE: str = "generate"
TRACE_PHASE_PALETTE_GENERATION: str = "palette_generation"
TRACE_AGENT_PALETTE_GENERATOR: str = "palette_generator"
TRACE_CONTENT_TYPE_PALETTE: str = "palette"

ERR_PALETTE_GENERATION_UNAVAILABLE: str = "palette_generation_unavailable"
ERR_DESCRIPTION_TOO_SHORT: str = "description is too short"

__all__ = [
    "CONTRAST_DECIMALS",
    "CONTRAST_REPAIR_STEP",
    "DESCRIPTION_MAX_LEN",
    "DESCRIPTION_MIN_LEN",
    "ERR_DESCRIPTION_TOO_SHORT",
    "ERR_PALETTE_GENERATION_UNAVAILABLE",
    "GENERATION_ATTEMPTS",
    "GENERATION_MAX_TOKENS",
    "GENERATION_TEMPERATURE",
    "GENERATION_TIMEOUT_SECONDS",
    "KEY_ACCENT",
    "KEY_BACKGROUND",
    "KEY_CANDIDATES",
    "KEY_KEYWORDS",
    "KEY_NAME",
    "KEY_PRIMARY",
    "MIX_TARGET_BLACK",
    "MIX_TARGET_WHITE",
    "PALETTE_CANDIDATE_COUNT",
    "PROMPT_DOMAIN_PALETTE",
    "PROMPT_PALETTE_GENERATE",
    "SLIDE_INK_ON_DARK",
    "SLIDE_INK_ON_LIGHT",
    "TRACE_AGENT_PALETTE_GENERATOR",
    "TRACE_CONTENT_TYPE_PALETTE",
    "TRACE_PHASE_PALETTE_GENERATION",
    "WCAG_AA_TEXT_CONTRAST",
]
