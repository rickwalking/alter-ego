"""What the daily scan may do about stuck autopilot runs.

List the runs that never got the owner's Retry and re-send one escalation notice.
Each call opens its own session; ``renotify`` commits one run at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.infrastructure.escalation_renotice import (
    SqlEscalationRenotices,
)


@dataclass(frozen=True, kw_only=True)
class RenoticeCandidate:
    """A stuck run and its carousel; the queue checks the carousel."""

    run_id: str
    project_id: str


@dataclass(frozen=True, kw_only=True)
class AutopilotRenoticeBridge:
    """The escalation re-notice, for the generation queue's scan."""

    sessions: async_sessionmaker[AsyncSession]

    async def candidates(self) -> list[RenoticeCandidate]:
        """Runs due a re-notice, oldest first."""
        async with self.sessions() as session:
            runs = await SqlEscalationRenotices(session).unsent()
        return [
            RenoticeCandidate(
                run_id=str(run.run_id), project_id=run.carousel_project_id or ""
            )
            for run in runs
        ]

    async def renotify(self, run_id: str) -> bool:
        """Stage one notice, committed; False when the run is no longer due."""
        async with self.sessions() as session:
            staged = await SqlEscalationRenotices(session).stage(UUID(run_id))
            await session.commit()
        return staged


__all__ = ["AutopilotRenoticeBridge", "RenoticeCandidate"]
