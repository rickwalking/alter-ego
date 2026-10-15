"""Ports for the scheduled publish (AE-0370). No frameworks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.domain.models import AutopilotRun


@dataclass(frozen=True, kw_only=True)
class DueScheduleQuery:
    """``scheduled`` runs whose time is at or before ``now``, oldest first."""

    now: datetime
    limit: int


class ScheduledRunSource(Protocol):
    """Reads due ``scheduled`` runs through the ``(state, scheduled_at)`` index."""

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """Due runs, earliest ``scheduled_at`` first, capped by ``query.limit``."""
        ...
