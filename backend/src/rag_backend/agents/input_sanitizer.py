"""Input sanitization helpers for LLM prompt construction."""

from rag_backend.domain.constants.input_sanitizer import INJECTION_PATTERNS, MAX_LLM_INPUT_LENGTH


def sanitize_llm_input(value: str) -> str:
    """Strip injection-prone characters and patterns from user-provided text."""
    cleaned = value.replace("<", "").replace(">", "").replace("(", "").replace(")", "")
    lowered = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        lowered = lowered.replace(pattern, "")
    cleaned = lowered[:MAX_LLM_INPUT_LENGTH]
    return cleaned.strip()


__all__ = ["sanitize_llm_input"]
