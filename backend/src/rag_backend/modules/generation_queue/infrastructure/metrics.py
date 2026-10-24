"""Read the queue's numbers from ``generation_runs`` and ``pg_stat_activity``.

The worker names its long-lived PgQueuer connection ``generation-worker``; while
that session exists the worker is up. Off Postgres the worker is reported down.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.constants import (
    STATUS_DEAD_LETTER,
    STATUS_QUEUED,
    STATUS_RETRY_WAIT,
    STATUS_RUNNING,
    WORKER_APPLICATION_NAME,
)
from rag_backend.modules.generation_queue.domain.health import QueueMetrics
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)

_POSTGRESQL = "postgresql"
_WORKER_SQL = text(
    "SELECT count(*) FROM pg_stat_activity WHERE application_name = :name"
)


def _age(now: datetime, moment: datetime | None) -> int:
    if moment is None:
        return 0
    return max(int((now - moment).total_seconds()), 0)


async def read_queue_metrics(engine: AsyncEngine, now: datetime) -> QueueMetrics:
    """Counts per status, the oldest queued and running ages, worker presence."""
    run = GenerationRunModel
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(run.status, func.count()).group_by(run.status)
        )
        counts: dict[str, int] = {str(row[0]): int(row[1]) for row in rows.all()}
        oldest = await connection.scalar(
            select(func.min(run.created_at)).where(run.status == STATUS_QUEUED)
        )
        started = await connection.scalar(
            select(func.min(run.started_at)).where(run.status == STATUS_RUNNING)
        )
        workers = 0
        if engine.dialect.name == _POSTGRESQL:
            workers = int(
                await connection.scalar(_WORKER_SQL, {"name": WORKER_APPLICATION_NAME})
                or 0
            )
    return QueueMetrics(
        queued=int(counts.get(STATUS_QUEUED, 0)),
        running=int(counts.get(STATUS_RUNNING, 0)),
        retry_wait=int(counts.get(STATUS_RETRY_WAIT, 0)),
        dead_letters=int(counts.get(STATUS_DEAD_LETTER, 0)),
        oldest_queued_seconds=_age(now, oldest),
        running_seconds=_age(now, started),
        worker_connected=workers > 0,
    )


__all__ = ["read_queue_metrics"]
