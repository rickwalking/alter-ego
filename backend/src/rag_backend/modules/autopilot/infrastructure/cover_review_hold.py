"""``CoverReviewHold`` on a fresh session per call (the website's background run).

The owner's website cover generation runs in a background task of the web
process; each hold or release opens its own session and commits it.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.cover_review_hold import (
    CoverReviewHold,
    CoverReviewHoldDeps,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.run_recovery_store import (
    SqlRunRecoveryStore,
)

SessionFactory = Callable[[], AsyncSession]


def _service(session: AsyncSession) -> CoverReviewHold:
    repo = SqlAlchemyAutopilotRepository(session)
    return CoverReviewHold(
        CoverReviewHoldDeps(
            runs=repo,
            recovery=SqlRunRecoveryStore(session),
            notices=SqlNoticeLogStore(session),
            checkpoint=repo,
            clock=SystemClock(),
        )
    )


class SessionCoverReviewHold:
    """The hold of the owner's Telegram review, one session per step."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def hold(self, project_id: str) -> UUID | None:
        """The held run, or None when no run waits for the owner's review."""
        async with self._sessions() as session:
            return await _service(session).hold(project_id)

    async def escalate(self, run_id: UUID, version: int | None) -> None:
        """Escalate the held run instead of handing the review back."""
        async with self._sessions() as session:
            await _service(session).escalate(run_id, version)

    async def release(self, run_id: UUID, *, changed: bool) -> None:
        """Hand the run back; ``changed`` lets the worker send the review again."""
        async with self._sessions() as session:
            await _service(session).release(run_id, changed=changed)

    async def reopened(self, project_id: str) -> None:
        """The carousel's approval was dropped: its run gets a new review."""
        async with self._sessions() as session:
            await _service(session).reopened(project_id)


__all__ = ["SessionCoverReviewHold"]
