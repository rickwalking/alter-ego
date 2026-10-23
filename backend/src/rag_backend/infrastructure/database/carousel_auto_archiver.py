"""Archive carousels that sat idle for N days (Pedro's decision).

Implements :class:`CarouselAutoArchiver`. A carousel is idle when it is not
published, its phase is not in progress, it is not archived yet and it was not
updated within the window. Archiving only sets ``archived_at``: the phase and
status stay as they were, so a restore puts the carousel back where it was.
Lives in infrastructure (owns the ORM query) so the worker gains no new
infrastructure import.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants.carousel_archive import AUTO_ARCHIVE_LOG_EVENT
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

logger = structlog.get_logger(__name__)


class CarouselIdleArchiver:
    """Sets ``archived_at`` on every idle carousel (see the module docstring)."""

    def __init__(self, clock: Callable[[], datetime] = utc_now) -> None:
        """Read the current time from ``clock`` (UTC)."""
        self._clock = clock

    async def archive_idle(self, db: AsyncSession, idle_days: int) -> int:
        """Archive the carousels idle for more than ``idle_days``; return the count."""
        now = self._clock()
        cutoff = now - timedelta(days=idle_days)
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.archived_at.is_(None),
                or_(
                    CarouselProjectModel.current_phase.is_(None),
                    CarouselProjectModel.current_phase != PHASE_PUBLISHED,
                ),
                or_(
                    CarouselProjectModel.phase_status.is_(None),
                    CarouselProjectModel.phase_status != PHASE_STATUS_IN_PROGRESS,
                ),
                CarouselProjectModel.updated_at <= cutoff,
            )
        )
        idle = list(result.scalars().all())
        for project in idle:
            project.archived_at = now
            logger.info(
                AUTO_ARCHIVE_LOG_EVENT,
                project_id=str(project.id),
                current_phase=project.current_phase,
                phase_status=project.phase_status,
                idle_days=idle_days,
            )
        await db.flush()
        return len(idle)


__all__ = ["CarouselIdleArchiver"]
