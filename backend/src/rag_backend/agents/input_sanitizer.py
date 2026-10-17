"""Input sanitization helpers for LLM prompt construction."""

import re

from rag_backend.domain.constants.input_sanitizer import (
    INJECTION_PATTERNS,
    MAX_LLM_INPUT_LENGTH,
)
from rag_backend.domain.copy_sanitize import sanitize_model_copy

_INJECTION_RE = re.compile(
    "|".join(re.escape(pattern) for pattern in INJECTION_PATTERNS),
    flags=re.IGNORECASE,
)


def _strip_injection_patterns(value: str) -> str:
    """Remove injection phrases case-insensitively until none is left.

    Repeats so a phrase rebuilt by a removal ("ignore previous ignore previous
    instructions instructions") is removed too. Case is preserved.
    """
    cleaned = value
    while True:
        stripped = _INJECTION_RE.sub("", cleaned)
        if stripped == cleaned:
            return cleaned
        cleaned = stripped


def _harden(value: str) -> str:
    cleaned = value.replace("<", "").replace(">", "").replace("(", "").replace(")", "")
    return _strip_injection_patterns(cleaned)[:MAX_LLM_INPUT_LENGTH].strip()


def sanitize_llm_input(value: str) -> str:
    """Strip injection-prone characters and patterns from text fed to an LLM.

    AE-0413: this used to lowercase the whole text (the patterns were matched
    on a lowercased copy). Topic, brief, audience and reviewer feedback reached
    the outline and drafting prompts in lowercase, and the model mirrored it:
    about 30 sentence-case blockers per run. The anti-injection intent is kept
    (``< > ( )`` stripped, injection phrases removed case-insensitively,
    length capped); only the case is preserved now. Same hardening as
    :func:`sanitize_display_input` (AE-0289).
    """
    return _harden(value)


def sanitize_display_input(value: str) -> str:
    """Sanitize user-edited FINAL published copy while PRESERVING case (AE-0289).

    Edited carousel slide copy is final display content; lowercasing it
    corrupted headings, acronyms and proper nouns and broke sentence-case
    validation. Since AE-0413 :func:`sanitize_llm_input` preserves case too, so
    both apply the same hardening: strip ``< > ( )`` and injection patterns
    (case-insensitively) and cap the length.
    """
    return _harden(value)


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


__all__ = [
    "sanitize_display_input",
    "sanitize_llm_input",
    "sanitize_model_copy",
    "sanitize_web_content",
]
