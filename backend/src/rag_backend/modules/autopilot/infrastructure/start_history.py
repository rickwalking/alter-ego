"""When the latest autopilot generation started, read from Postgres.

A start is the creation of the run's carousel project, which the runner does
right before it moves the run to ``generating``; no extra column is needed.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, column, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.constants import CAROUSEL_PROJECTS_TABLE
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware

_CAROUSELS = table(
    CAROUSEL_PROJECTS_TABLE,
    column("id", String),
    column("created_at", DateTime(timezone=True)),
)


class SqlStartHistory:
    """``StartHistory`` over ``autopilot_runs`` joined to ``carousel_projects``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_start(self, exclude_run: UUID) -> datetime | None:
        """The newest carousel creation of any other autopilot run."""
        statement = (
            select(func.max(_CAROUSELS.c.created_at))
            .select_from(AutopilotRunModel)
            .join(_CAROUSELS, _CAROUSELS.c.id == AutopilotRunModel.carousel_project_id)
            .where(AutopilotRunModel.id != exclude_run)
        )
        latest: datetime | None = await self._session.scalar(statement)
        return aware(latest)
