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


def render_facts(marked_at: datetime | None, now: datetime) -> RenderFacts:
    """The facts for a marker stamped at ``marked_at`` (None: no render owed)."""
    if marked_at is None:
        return RenderFacts(pending=False, overdue=False)
    if marked_at.tzinfo is None:
        marked_at = marked_at.replace(tzinfo=UTC)
    limit = timedelta(seconds=RENDER_PENDING_MAX_SECONDS)
    return RenderFacts(pending=True, overdue=now - marked_at >= limit)


__all__ = ["RenderFacts", "render_facts"]
