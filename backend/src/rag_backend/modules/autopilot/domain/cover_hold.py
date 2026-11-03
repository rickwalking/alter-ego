"""A website cover switch holding a run's Telegram review. No I/O.

The hold queues the ``website_cover`` rework with its start time as the
feedback (ISO 8601), so the run keeps its ``updated_at``, the anchor of the
review's 72-hour window. The worker skips an active hold and drops one older
than ``COVER_REVIEW_HOLD_MAX_SECONDS`` (its task died).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from rag_backend.modules.autopilot.cover_constants import (
    COVER_REVIEW_HOLD_MAX_SECONDS,
    COVER_REVIEW_HOLD_PHASE,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun


def hold_started(feedback: str | None) -> datetime | None:
    """The hold's start time stored in the rework feedback, else None."""
    if not feedback:
        return None
    try:
        return datetime.fromisoformat(feedback)
    except ValueError:
        return None


def is_held(run: AutopilotRun) -> bool:
    """True while ``run`` carries the website cover hold (active or outlived)."""
    return run.rework_phase == COVER_REVIEW_HOLD_PHASE


def hold_active(run: AutopilotRun, now: datetime) -> bool:
    """True while the hold is younger than its limit; an undated hold is outlived."""
    if not is_held(run):
        return False
    started = hold_started(run.rework_feedback)
    if started is None:
        return False
    return now < started + timedelta(seconds=COVER_REVIEW_HOLD_MAX_SECONDS)


__all__ = ["hold_active", "hold_started", "is_held"]
