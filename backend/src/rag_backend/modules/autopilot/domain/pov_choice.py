"""The scout v3 POV format and slide count of one topic (PR #106 review, item 6).

The scout picks ``pov_format`` and ``slide_count`` per POV topic; the schema
validates them against ``POV_FORMATS`` and the 8-10 range. A Radar IA topic
never carries them. The run falls back to ``DEFAULT_POV_FORMAT`` and
``POV_SLIDE_COUNT_DEFAULT`` only when the scout left them out.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_POV_NEWS,
    DEFAULT_POV_FORMAT,
    POV_SLIDE_COUNT_DEFAULT,
)
from rag_backend.domain.content_mode import is_pov_family


@dataclass(frozen=True, kw_only=True)
class PovChoice:
    """The scout's POV format and slide count; None = not chosen."""

    pov_format: str | None = None
    slide_count: int | None = None


NO_POV_CHOICE = PovChoice()


def pov_choice_for(content_mode: str | None, choice: PovChoice) -> PovChoice:
    """The choice a topic stores: empty for a Radar IA topic.

    AE-0406: ``pov_news`` keeps the slide count and ignores the format.
    """
    if not is_pov_family(content_mode):
        return NO_POV_CHOICE
    if content_mode == CONTENT_MODE_POV_NEWS:
        return PovChoice(slide_count=choice.slide_count)
    return choice


def resolved_pov_format(choice: PovChoice) -> str:
    """The scout's format, or the default when it chose none."""
    return choice.pov_format or DEFAULT_POV_FORMAT


def resolved_slide_count(choice: PovChoice) -> int:
    """The scout's slide count, or 9 when it chose none."""
    return choice.slide_count or POV_SLIDE_COUNT_DEFAULT


__all__ = [
    "NO_POV_CHOICE",
    "PovChoice",
    "pov_choice_for",
    "resolved_pov_format",
    "resolved_slide_count",
]
