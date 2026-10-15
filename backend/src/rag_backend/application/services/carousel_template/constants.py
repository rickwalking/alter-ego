from __future__ import annotations

from rag_backend.domain.constants import LANGUAGE_EN, SWIPE_TEXT_EN, SWIPE_TEXT_PT

SWIPE_TEXT = SWIPE_TEXT_EN


def swipe_text_for(language: str) -> str:
    """The swipe hint in the slide's locale (AE-0372: "Deslize →" on PT slides)."""
    return SWIPE_TEXT_EN if language == LANGUAGE_EN else SWIPE_TEXT_PT


__all__ = ["SWIPE_TEXT", "swipe_text_for"]
