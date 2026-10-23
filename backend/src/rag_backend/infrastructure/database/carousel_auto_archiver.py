"""Archive carousels that sat idle for N days.

Implements :class:`CarouselAutoArchiver` with the rules of
``carousel_archive_rules``: not published, no live run, no autopilot run still
going (a carousel scheduled to publish is kept), not generating and not updated
within the window. One conditional UPDATE archives them, so a carousel that
starts a run or gets scheduled meanwhile is never archived. Archiving only sets
``archived_at``: the phase and status stay as they were, so a restore puts the
carousel back where it was.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants.carousel_archive import AUTO_ARCHIVE_LOG_EVENT
from rag_backend.infrastructure.database.models import (
    archive_where,
    auto_archivable,
)

logger = structlog.get_logger(__name__)


class CarouselIdleArchiver:
    """Archives every idle carousel (see the module docstring)."""

    def __init__(
        self, stale_seconds: int, clock: Callable[[], datetime] = utc_now
    ) -> None:
        """``stale_seconds``: a run heartbeat older than this is not a live run."""
        self._stale_seconds = stale_seconds
        self._clock = clock

    async def archive_idle(self, db: AsyncSession, idle_days: int) -> int:
        """Archive the carousels idle for more than ``idle_days``; return the count."""
        now = self._clock()
        predicates = auto_archivable(
            now, self._stale_seconds, now - timedelta(days=idle_days)
        )
        archived = await archive_where(db, predicates, now)
        for project_id in archived:
            logger.info(
                AUTO_ARCHIVE_LOG_EVENT, project_id=project_id, idle_days=idle_days
            )
        return len(archived)


__all__ = ["CarouselIdleArchiver"]
