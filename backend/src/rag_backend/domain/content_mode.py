"""Content-mode predicates shared by every layer (AE-0406, ADR-0023).

``pov`` and ``pov_news`` form the POV family: both take the thesis step, the
slide-1 photo, the ``pov_hook_v1`` contract and the voice gate. Only the
prompt family (the voice) tells them apart.
"""

from __future__ import annotations

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_POV_NEWS,
    POV_FAMILY_MODES,
)
from rag_backend.domain.constants.pov_prompts import (
    POV_NEWS_PROMPT_DOMAIN,
    POV_PROMPT_DOMAIN,
)


def is_pov_family(content_mode: str | None) -> bool:
    """True for ``pov`` and ``pov_news`` (None / ``news_analysis`` are Radar IA)."""
    return content_mode in POV_FAMILY_MODES


def is_pov_news(content_mode: str | None) -> bool:
    """True only for the news-analysis POV mode."""
    return content_mode == CONTENT_MODE_POV_NEWS


def pov_prompt_domain(content_mode: str | None) -> str:
    """The POV prompt family of a mode: ``carousel_pov_news`` or ``carousel_pov``."""
    if is_pov_news(content_mode):
        return POV_NEWS_PROMPT_DOMAIN
    return POV_PROMPT_DOMAIN


__all__ = ["is_pov_family", "is_pov_news", "pov_prompt_domain"]
