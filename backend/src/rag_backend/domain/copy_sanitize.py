"""Case- and markup-preserving sanitizer for pipeline-generated copy.

Outline titles/key points and drafted slide copy are model output that is fed
back into the content drafter and the EN translator. The lowercasing
``sanitize_llm_input`` turned "A versão para robótica leva o Argon ..." into
"a versão ... o argon ..." and ``<strong>`` into a bare ``strong``, and the
models faithfully echoed the damage into the slides. This keeps the
injection-pattern defense and the length cap but preserves case, inline markup
and parentheses.

The only markup a reviewer edit may carry is the EN ``<strong>`` tag pair.
Tag-like spans are ``<script>``, ``</div>``, ``<!-- -->``; a bare ``a < b`` is
not one.
"""

from __future__ import annotations

import re

from rag_backend.domain.constants.input_sanitizer import (
    EDITED_COPY_STRIPPED_CHARS,
    INJECTION_PATTERNS,
    MAX_LLM_INPUT_LENGTH,
)

_EMPHASIS_TAG_SPLIT = re.compile(r"(</?strong>)", flags=re.IGNORECASE)
_MARKUP_TAG = re.compile(r"<[a-zA-Z/!][^<>]*>")


def sanitize_model_copy(value: str) -> str:
    """Strip injection patterns (any case) and cap length; keep case and markup."""
    cleaned = value
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(re.escape(pattern), "", cleaned, flags=re.IGNORECASE)
    return cleaned[:MAX_LLM_INPUT_LENGTH].strip()


def _neutralize_markup(segment: str) -> str:
    """Drop tag-like spans, then any stray injection-prone character."""
    cleaned = _MARKUP_TAG.sub("", segment)
    for char in EDITED_COPY_STRIPPED_CHARS:
        cleaned = cleaned.replace(char, "")
    return cleaned


def sanitize_edited_copy(value: str) -> str:
    """Sanitize reviewer-edited FINAL slide copy.

    Keeps case, PT ``**`` emphasis and the EN ``<strong>``/``</strong>`` pair
    (normalized to lowercase), while every other tag, stray ``< > ( )`` and the
    injection patterns are stripped and the length is capped. The old
    ``sanitize_display_input`` path turned ``<strong>x</strong>`` into
    ``strongx/strong``, which the validator then refused as
    ``emphasis_markup_invalid``.
    """
    parts = _EMPHASIS_TAG_SPLIT.split(value)
    kept = [
        part.lower() if index % 2 else _neutralize_markup(part)
        for index, part in enumerate(parts)
    ]
    cleaned = "".join(kept)
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(re.escape(pattern), "", cleaned, flags=re.IGNORECASE)
    return cleaned[:MAX_LLM_INPUT_LENGTH].strip()


__all__ = ["sanitize_edited_copy", "sanitize_model_copy"]
