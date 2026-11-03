"""Ports for the scheduled publish. No frameworks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.recommend import ScheduleSignals


@dataclass(frozen=True, kw_only=True)
class DueScheduleQuery:
    """Runs whose time is at or before ``now``, oldest first: ``scheduled``
    ones and reopened ones waiting with their time kept. ``offset`` pages."""

    now: datetime
    limit: int
    offset: int = 0


class ScheduledRunSource(Protocol):
    """Reads due ``scheduled`` runs through the ``(state, scheduled_at)`` index."""

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """Due runs, earliest ``scheduled_at`` first, capped by ``query.limit``."""
        ...

    async def waiting(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """``scheduled`` runs whose time is still ahead of ``query.now``."""
        ...


class CarouselRowLock(Protocol):
    """Locks a carousel row until the caller's transaction ends."""

    async def lock(self, project_id: str) -> None:
        """``SELECT ... FOR UPDATE``: a concurrent slide-1 switch waits."""
        ...


class ScheduleSignalsSource(Protocol):
    """The audience and post-engagement signals of the slot recommender."""

    async def load(self) -> ScheduleSignals:
        """Never raises for a Graph failure: it falls back to cached or no data."""
        ...


class AudienceGateway(Protocol):
    """Reads the account's ``online_followers`` from the Graph API."""

    async def online_followers(self) -> dict[int, int]:
        """Followers online per UTC hour (0-23). Raises when Graph cannot answer."""
        ...
