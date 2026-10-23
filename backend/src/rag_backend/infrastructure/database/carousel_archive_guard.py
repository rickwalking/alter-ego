"""Working on an archived carousel brings it back to the active board.

A ``before_update`` listener on :class:`CarouselProjectModel` clears
``archived_at`` in the same flush when an archived carousel starts a phase run
(``phase_status`` becomes ``in_progress``) or gets an owner edit (its content
or ``lock_version`` changes), for example through a direct link to an archived
carousel. Bookkeeping writes (run heartbeat, a failed or rejected phase) keep it
archived, and a flush that sets ``archived_at`` itself is left alone.

Self-registers on import, like the run guard; the models package imports it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import event
from sqlalchemy.orm.attributes import get_history

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.orm import Mapper

_ARCHIVED_AT = "archived_at"
_PHASE_STATUS = "phase_status"
OWNER_ACTIVITY_COLUMNS: tuple[str, ...] = (
    "lock_version",
    "topic",
    "audience",
    "niche",
    "title",
    "subtitle",
    "title_en",
    "subtitle_en",
    "slides_config",
    "caption",
    "caption_en",
    "linkedin_post_pt",
    "linkedin_post_en",
    "blog_markdown",
    "creative_brief",
    "instructions",
    "custom_visual_details",
    "design_tokens",
    "persona_id",
    "rubric_id",
)
"""Columns whose change is the owner working on the carousel."""


def _changed(target: CarouselProjectModel, attribute: str) -> bool:
    history = get_history(target, attribute)
    if not history.added:
        return False
    old = history.deleted[0] if history.deleted else None
    return bool(history.added[0] != old)


def _starts_a_run(target: CarouselProjectModel) -> bool:
    return (
        _changed(target, _PHASE_STATUS)
        and target.phase_status == PHASE_STATUS_IN_PROGRESS
    )


def _unarchive_on_activity(
    _mapper: Mapper[CarouselProjectModel],
    _connection: Connection,
    target: CarouselProjectModel,
) -> None:
    """Clear ``archived_at`` when an archived carousel is worked on."""
    if target.archived_at is None or _changed(target, _ARCHIVED_AT):
        return
    if _starts_a_run(target) or any(
        _changed(target, name) for name in OWNER_ACTIVITY_COLUMNS
    ):
        target.archived_at = None


class _GuardRegistry:
    """Idempotent one-shot registration flag."""

    registered: bool = False


def register_carousel_archive_guard() -> None:
    """Attach the un-archive listener (idempotent)."""
    if _GuardRegistry.registered:
        return
    _GuardRegistry.registered = True
    event.listen(CarouselProjectModel, "before_update", _unarchive_on_activity)


register_carousel_archive_guard()
