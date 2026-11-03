"""How long a final review has waited for a render the slides owe. No I/O.

The worker sends no final review while the needs-republish marker is set, so
the review always shows the rendered slides. A render that never lands must
not keep the run silent: after ``RENDER_PENDING_MAX_SECONDS`` the run is
escalated and the owner is told.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from rag_backend.modules.autopilot.constants import RENDER_PENDING_MAX_SECONDS


@dataclass(frozen=True, kw_only=True)
class RenderFacts:
    """A render is owed, and it has been owed for longer than the bound."""

    pending: bool
    overdue: bool


def render_facts(
    marked_at: datetime | None, now: datetime, waiting_since: datetime | None = None
) -> RenderFacts:
    """The facts for a marker stamped at ``marked_at`` (None: no render owed).

    The wait is timed from the later of the marker and ``waiting_since`` (the
    last heartbeat of a run, i.e. when the workflow came to rest at the final
    review): a marker stamped before a long rework, while the republish sweep
    could not render, does not escalate the moment the review is reached.
    """
    if marked_at is None:
        return RenderFacts(pending=False, overdue=False)
    start = max(_aware(marked_at), _aware(waiting_since or marked_at))
    limit = timedelta(seconds=RENDER_PENDING_MAX_SECONDS)
    return RenderFacts(pending=True, overdue=now - start >= limit)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


__all__ = ["RenderFacts", "render_facts"]
