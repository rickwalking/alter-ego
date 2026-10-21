"""Constants for LLM input sanitization.

``EDITED_COPY_STRIPPED_CHARS`` are stripped from reviewer-edited copy outside the
emphasis tags.
"""

MAX_LLM_INPUT_LENGTH = 10_000

INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "system prompt",
    "you are now",
)

EDITED_COPY_STRIPPED_CHARS: tuple[str, ...] = ("<", ">", "(", ")")

__all__ = ["EDITED_COPY_STRIPPED_CHARS", "INJECTION_PATTERNS", "MAX_LLM_INPUT_LENGTH"]
