"""Input sanitization helpers for LLM prompt construction."""

import re

from rag_backend.domain.constants.input_sanitizer import (
    INJECTION_PATTERNS,
    MAX_LLM_INPUT_LENGTH,
)


def sanitize_llm_input(value: str) -> str:
    """Strip injection-prone characters and patterns from user-provided text."""
    cleaned = value.replace("<", "").replace(">", "").replace("(", "").replace(")", "")
    lowered = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        lowered = lowered.replace(pattern, "")
    cleaned = lowered[:MAX_LLM_INPUT_LENGTH]
    return cleaned.strip()


_HTML_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_web_content(value: str) -> str:
    """Sanitize scraped web content for LLM consumption.

    Gentler than sanitize_llm_input:
    - Strips HTML tags (but not parens or angle brackets in text)
    - Strips injection patterns
    - Preserves case (acronyms, proper nouns)
    - Preserves parentheses (code, math, URLs)
    - No length truncation (already truncated in scrape_url)
    """
    cleaned = _HTML_TAG_RE.sub("", value)
    lowered = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        lowered = lowered.replace(pattern, "")
    if lowered != cleaned:
        for pattern in INJECTION_PATTERNS:
            cleaned = cleaned.replace(pattern, "")
            cleaned = cleaned.replace(pattern.capitalize(), "")
            cleaned = cleaned.replace(pattern.title(), "")
    return cleaned.strip()


__all__ = ["sanitize_llm_input", "sanitize_web_content"]
