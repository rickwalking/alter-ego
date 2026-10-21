"""Domain-level constants for persona and voice management.

A stored persona overall in (0, 10] is a 0-10 answer and is read x10. A persona
judge call that errors, times out or answers no usable overall is retried once;
a second failure leaves the slide unscored.
"""

TONE_CONVERSATIONAL = 0.8
TONE_FORMAL = 0.3
TONE_HUMOROUS = 0.4

DEFAULT_TONE_ATTRIBUTES = {
    "formal": TONE_FORMAL,
    "conversational": TONE_CONVERSATIONAL,
    "humorous": TONE_HUMOROUS,
}

VOICE_MATCH_MIN_SCORE = 70.0

PERSONA_SCORE_TEN_POINT_MAX = 10.0
PERSONA_SCORE_TEN_TO_HUNDRED = 10.0

PERSONA_JUDGE_CALLS = 2
PERSONA_JUDGE_TIMEOUT_SECONDS = 120.0
LOG_PERSONA_JUDGE_FAILED = "persona_judge_failed"
PERSONA_JUDGE_REASON_ERROR = "error"
PERSONA_JUDGE_REASON_NO_SCORE = "no_score"

ERR_PERSONA_NOT_FOUND = "persona_not_found"

__all__ = [
    "DEFAULT_TONE_ATTRIBUTES",
    "ERR_PERSONA_NOT_FOUND",
    "LOG_PERSONA_JUDGE_FAILED",
    "PERSONA_JUDGE_CALLS",
    "PERSONA_JUDGE_REASON_ERROR",
    "PERSONA_JUDGE_REASON_NO_SCORE",
    "PERSONA_JUDGE_TIMEOUT_SECONDS",
    "PERSONA_SCORE_TEN_POINT_MAX",
    "PERSONA_SCORE_TEN_TO_HUNDRED",
    "TONE_CONVERSATIONAL",
    "TONE_FORMAL",
    "TONE_HUMOROUS",
    "VOICE_MATCH_MIN_SCORE",
]
