"""Pick the CTA slide sentence for a goal and locale."""

from __future__ import annotations

from rag_backend.domain.constants import LANGUAGE_EN
from rag_backend.domain.constants.carousel_cta import (
    CTA_COPY_EN,
    CTA_COPY_PT,
    DEFAULT_CTA_GOAL,
)


def handle_with_at(handle: str) -> str:
    """``pedromarins.ai`` → ``@pedromarins.ai``; an ``@`` already there is kept."""
    return handle if handle.startswith("@") else f"@{handle}"


def cta_copy(goal: str | None, language: str, handle: str) -> str:
    """The CTA sentence for ``goal`` (unknown or None → follow) in ``language``."""
    table = CTA_COPY_EN if language == LANGUAGE_EN else CTA_COPY_PT
    template = table.get(goal or DEFAULT_CTA_GOAL, table[DEFAULT_CTA_GOAL])
    return template.format(handle=handle_with_at(handle))


__all__ = ["cta_copy", "handle_with_at"]
