"""Domain-level constants for persona and voice management."""

# Default tone attributes
TONE_CONVERSATIONAL = 0.8
TONE_FORMAL = 0.3
TONE_HUMOROUS = 0.4

# Default tone attributes dict
DEFAULT_TONE_ATTRIBUTES = {
    "formal": TONE_FORMAL,
    "conversational": TONE_CONVERSATIONAL,
    "humorous": TONE_HUMOROUS,
}

VOICE_MATCH_MIN_SCORE = 70.0

# AE-0407: a stored persona overall in (0, 10] is a 0-10 answer, read x10.
PERSONA_SCORE_TEN_POINT_MAX = 10.0
PERSONA_SCORE_TEN_TO_HUNDRED = 10.0

ERR_PERSONA_NOT_FOUND = "persona_not_found"

__all__ = [
    "DEFAULT_TONE_ATTRIBUTES",
    "ERR_PERSONA_NOT_FOUND",
    "PERSONA_SCORE_TEN_POINT_MAX",
    "PERSONA_SCORE_TEN_TO_HUNDRED",
    "TONE_CONVERSATIONAL",
    "TONE_FORMAL",
    "TONE_HUMOROUS",
    "VOICE_MATCH_MIN_SCORE",
]
