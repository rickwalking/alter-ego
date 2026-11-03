"""Server-guaranteed republish sweeper for edited carousels.

Runs in the workflow-workers tick AFTER the drift reconciler (pinned ordering).
A post-completion slide edit stamps ``needs_republish_since`` in the same
transaction as the slide write and the client triggers the republish for fast
feedback — but a browser closed between the edit 200 and the republish call would
otherwise leave corrected text with a stale public PDF (the 66014ba3 incident
reskinned; cold-critic r6). This watchdog closes that gap: it republishes any
completed project whose marker is older than a few minutes and clears the marker
on success. Fresh edits are already cleared by the client's own republish, so
only abandoned edits reach the sweep.

A concurrent client republish holds the shared advisory lock; the republish call
raises ``build_in_progress`` in that window, which the sweep swallows (the client
is already rebuilding) and retries on a later tick.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_slide_edit import (
    LOG_EVENT_REPUBLISH_COVER_REFUSED,
    LOG_EVENT_REPUBLISH_SWEPT,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_CHANGE_REQUIRES_REVIEW,
)
from rag_backend.domain.models.carousel import CarouselStatus
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

logger = structlog.get_logger()


def _as_utc(value: datetime) -> datetime:
    """Normalize naive timestamps (SQLite) to aware UTC for comparisons."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


@dataclass(frozen=True)
class CarouselRepublishSweeperConfig:
    """Sweep threshold (from Settings at the composition root)."""

    min_age_seconds: int


class CarouselRepublishSweeperRepository:
    """ORM-backed implementation of :class:`CarouselRepublishSweeper`."""

    def __init__(self, config: CarouselRepublishSweeperConfig) -> None:
        self._config = config
        self._cover_refused: dict[str, int] = {}

    async def sweep(self, db: AsyncSession) -> int:
        """Republish every overdue-marked completed carousel; return the count.

        A row refused because its slide-1 cover would change unreviewed on an
        approved or public carousel is logged once and skipped until its lock
        version moves (worker-scoped memory, like the stale-run reaper's counts).
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=self._config.min_age_seconds)
        rows = await self._overdue_rows(db)
        republished = 0
        for row in rows:
            marker = row.needs_republish_since
            if marker is None or _as_utc(marker) > cutoff:
                continue
            project_id, version = str(row.id), int(row.lock_version or 1)
            if self._cover_refused.get(project_id) == version:
                continue
            errors = await _republish_row(db, project_id)
            if errors is None:
                republished += 1
                self._cover_refused.pop(project_id, None)
            elif ERR_COVER_CHANGE_REQUIRES_REVIEW in errors:
                self._cover_refused[project_id] = version
                logger.error(LOG_EVENT_REPUBLISH_COVER_REFUSED, project_id=project_id)
        return republished

    @staticmethod
    async def _overdue_rows(db: AsyncSession) -> list[CarouselProjectModel]:
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.needs_republish_since.is_not(None),
                CarouselProjectModel.status == CarouselStatus.COMPLETED.value,
            )
        )
        return list(result.scalars().all())


async def _republish_row(db: AsyncSession, project_id: str) -> tuple[str, ...] | None:
    """Republish one marked project + clear the marker; None on success.

    Otherwise the errors; a conflict means a client republish holds the lock and
    it is retried next tick.
    """
    from rag_backend.application.services.carousel.carousel_republish import (
        republish_completed_carousel,
    )
    from rag_backend.modules.editorial.public import CarouselProjectWriteOwner

    rendered_from = datetime.now(UTC)
    try:
        result = await republish_completed_carousel(db, project_id)
    except CarouselConflictError as exc:
        return (exc.conflict.code,)
    if not result.completed:
        return result.errors
    await CarouselProjectWriteOwner(db).clear_needs_republish(project_id, rendered_from)
    logger.info(LOG_EVENT_REPUBLISH_SWEPT, project_id=project_id)
    return None


__all__ = [
    "CarouselRepublishSweeperConfig",
    "CarouselRepublishSweeperRepository",
]
