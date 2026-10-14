"""Carousel facts the Instagram publish job reads. No ORM types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class InstagramPublishTarget:
    """Workflow, visibility, caption, and slide numbers for one carousel."""

    workflow_status: str
    status: str
    is_public: bool
    caption: str
    slide_numbers: tuple[int, ...]
