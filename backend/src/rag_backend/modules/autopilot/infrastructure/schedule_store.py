"""SQLAlchemy reader for due ``scheduled`` runs (AE-0370).

Split from ``repository.py`` so the adapter stays under 400 lines.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.schedule_ports import DueScheduleQuery
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.run_mapping import run_from_row


class SqlScheduledRuns:
    """Session-scoped ``ScheduledRunSource``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        """Due runs, earliest first. A run without a time is never due."""
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(
                AutopilotRunModel.state == AutopilotRunState.SCHEDULED.value,
                AutopilotRunModel.scheduled_at.is_not(None),
                AutopilotRunModel.scheduled_at <= query.now,
            )
            .order_by(AutopilotRunModel.scheduled_at.asc())
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        return [run_from_row(row) for row in result.scalars().all()]
