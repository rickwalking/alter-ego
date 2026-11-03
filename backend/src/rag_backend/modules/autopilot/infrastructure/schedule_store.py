"""SQLAlchemy reader for due runs, and the carousel row lock of the due sweep.

Split from ``repository.py`` so the adapter stays under 400 lines. A due run
is ``scheduled``, or ``awaiting_owner`` / ``reworking`` with its
``scheduled_at`` kept: a reopened review (only a reopen keeps the time outside
``scheduled``), still waiting for its new review or for a render.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.schedule_ports import DueScheduleQuery
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.run_mapping import run_from_row
from rag_backend.modules.editorial.public import lock_carousel_row, review_reopened

_DUE_STATES = (
    AutopilotRunState.SCHEDULED.value,
    AutopilotRunState.AWAITING_OWNER.value,
    AutopilotRunState.REWORKING.value,
)


class EditorialCarouselRowLock:
    """``CarouselRowLock`` through the editorial facade, on the tick's session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock(self, project_id: str) -> None:
        """Lock the carousel row (and refresh it) until the tick commits."""
        await lock_carousel_row(self._session, project_id)


class SqlScheduledRuns:
    """Session-scoped ``ScheduledRunSource``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """Due runs, earliest first. A run without a time is never due."""
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(
                AutopilotRunModel.state.in_(_DUE_STATES),
                AutopilotRunModel.scheduled_at.is_not(None),
                AutopilotRunModel.scheduled_at <= query.now,
            )
            .order_by(AutopilotRunModel.scheduled_at.asc())
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        return [run_from_row(row) for row in result.scalars().all()]

    async def waiting(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """``scheduled`` runs not due yet, earliest first, one page."""
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(
                AutopilotRunModel.state == AutopilotRunState.SCHEDULED.value,
                AutopilotRunModel.scheduled_at > query.now,
            )
            .order_by(AutopilotRunModel.scheduled_at.asc(), AutopilotRunModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        return [run_from_row(row) for row in result.scalars().all()]


class EditorialReopenedReviews:
    """``ReopenedReviewSource`` through the editorial facade."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reopened(self, project_id: str) -> bool:
        """A completed draft waiting in final review, not released."""
        return await review_reopened(self._session, project_id)
