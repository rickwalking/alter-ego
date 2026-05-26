"""Constants for LLM input sanitization."""

MAX_LLM_INPUT_LENGTH = 10_000

INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "system prompt",
    "you are now",
)

__all__ = ["INJECTION_PATTERNS", "MAX_LLM_INPUT_LENGTH"]
