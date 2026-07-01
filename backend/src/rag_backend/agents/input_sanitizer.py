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


def sanitize_display_input(value: str) -> str:
    """Sanitize user-edited FINAL published copy while PRESERVING case (AE-0289).

    ``sanitize_llm_input`` lowercases text because it hardens strings that are fed
    back into an LLM prompt. Edited carousel slide copy is final display content,
    not prompt input — lowercasing it corrupts headings/acronyms/proper nouns and
    breaks sentence-case validation (``heading_not_sentence_case_en``). This keeps
    the same injection defenses (strip ``< > ( )`` and injection patterns, cap
    length) but leaves case intact by matching patterns case-insensitively.
    """
    cleaned = value.replace("<", "").replace(">", "").replace("(", "").replace(")", "")
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(re.escape(pattern), "", cleaned, flags=re.IGNORECASE)
    return cleaned[:MAX_LLM_INPUT_LENGTH].strip()


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


__all__ = ["sanitize_display_input", "sanitize_llm_input", "sanitize_web_content"]
