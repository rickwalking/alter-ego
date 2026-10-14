"""Case- and markup-preserving sanitizer for pipeline-generated copy (AE-0366).

Outline titles/key points and drafted slide copy are model output that is fed
back into the content drafter and the EN translator. The lowercasing
``sanitize_llm_input`` turned "A versão para robótica leva o Argon ..." into
"a versão ... o argon ..." and ``<strong>`` into a bare ``strong``, and the
models faithfully echoed the damage into the slides. This keeps the
injection-pattern defense and the length cap but preserves case, inline markup
and parentheses.
"""

from __future__ import annotations

import re

from rag_backend.domain.constants.input_sanitizer import (
    INJECTION_PATTERNS,
    MAX_LLM_INPUT_LENGTH,
)


def sanitize_model_copy(value: str) -> str:
    """Strip injection patterns (any case) and cap length; keep case and markup."""
    cleaned = value
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(re.escape(pattern), "", cleaned, flags=re.IGNORECASE)
    return cleaned[:MAX_LLM_INPUT_LENGTH].strip()


__all__ = ["sanitize_model_copy"]
