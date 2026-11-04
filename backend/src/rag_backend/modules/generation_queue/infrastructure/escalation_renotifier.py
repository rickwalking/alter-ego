"""``EscalationRenotifier`` over the autopilot's re-notice bridge.

The autopilot lists its stuck runs; this adapter keeps those whose carousel can
still be retried. It mirrors the Retry's ``_finished`` guard and also drops an
archived carousel and a running one. A carousel that is only running is dropped
without a marker, so a later scan can still pick its run up. The same check runs
again when a notice is staged, holding the carousel row until that commit.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.renotice_bridge import AutopilotRenoticeBridge

_C = CarouselProjectModel
_SETTLED_PHASE_STATUSES = (
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
)
_OPEN_CAROUSEL = (
    _C.archived_at.is_(None),
    _C.workflow_status != WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
    or_(_C.current_phase.is_(None), _C.current_phase != PHASE_PUBLISHED),
    or_(_C.phase_status.is_(None), _C.phase_status.not_in(_SETTLED_PHASE_STATUSES)),
)


class SqlEscalationRenotifier:
    """Implements ``EscalationRenotifier``."""

    def __init__(
        self,
        bridge: AutopilotRenoticeBridge,
        sessions: async_sessionmaker[AsyncSession],
    ) -> None:
        self._bridge = bridge
        self._sessions = sessions

    async def stuck_runs(self) -> list[str]:
        """Runs due a re-notice whose carousel is still open, oldest first."""
        candidates = await self._bridge.candidates()
        open_projects = await self._open_projects([
            candidate.project_id for candidate in candidates
        ])
        return [
            candidate.run_id
            for candidate in candidates
            if candidate.project_id in open_projects
        ]

    async def renotify(self, run_id: str) -> bool:
        """Stage the run's one notice; False when it is no longer eligible."""
        return await self._bridge.renotify(run_id, _carousel_open)

    async def _open_projects(self, project_ids: list[str]) -> set[str]:
        async with self._sessions() as session:
            result = await session.execute(
                select(_C.id).where(_C.id.in_(project_ids), *_OPEN_CAROUSEL)
            )
            return {str(project_id) for project_id in result.scalars().all()}


async def _carousel_open(session: AsyncSession, project_id: str) -> bool:
    """The carousel can still be retried; a shared lock holds it until the commit."""
    result = await session.execute(
        select(_C.id)
        .where(_C.id == project_id, *_OPEN_CAROUSEL)
        .with_for_update(read=True)
    )
    return result.scalar_one_or_none() is not None


__all__ = ["SqlEscalationRenotifier"]
