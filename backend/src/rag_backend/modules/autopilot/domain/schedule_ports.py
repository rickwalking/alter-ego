"""Ports for the scheduled publish (AE-0370, AE-0404). No frameworks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.recommend import ScheduleSignals


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


class ScheduleSignalsSource(Protocol):
    """The audience and post-engagement signals of the slot recommender (AE-0404)."""

    async def load(self) -> ScheduleSignals:
        """Never raises for a Graph failure: it falls back to cached or no data."""
        ...


class AudienceGateway(Protocol):
    """Reads the account's ``online_followers`` from the Graph API (AE-0404)."""

    async def online_followers(self) -> dict[int, int]:
        """Followers online per UTC hour (0-23). Raises when Graph cannot answer."""
        ...
