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


@dataclass(frozen=True, kw_only=True)
class StoryImageTarget:
    """The Story image state and the facts the music nudge reads (AE-0369).

    ``ready`` is False when slide 1 was never rendered or the Story could not
    be written; the publish job then records the Story as failed.
    """

    ready: bool
    niche: str
    image_style: str
