"""Read the queue order and requeue a parked autopilot drive, in the caller's session.

The Telegram webhook shows a run's queue position and retries a dead letter inside
its own transaction: the autopilot run's state change and the generation run's
requeue commit together, so the dispatcher never sees one without the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, Update, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    KIND_AUTOPILOT_DRIVE,
    STATUS_DEAD_LETTER,
    STATUS_QUEUED,
    STATUS_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain import budget
from rag_backend.modules.generation_queue.domain.budget import AttemptCounts
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.domain.models import GenerationRun
from rag_backend.modules.generation_queue.domain.priority import priority_of
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    run_from_row,
)

_SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True, kw_only=True)
class QueuedWork:
    """One active generation run with all position and ETA metadata."""

    autopilot_run_id: str | None
    created_at: datetime
    id: str = ""
    status: str = STATUS_QUEUED
    priority: int = 0
    pgq_job_id: int | None = None
    started_at: datetime | None = None
    next_attempt_at: datetime | None = None
    staged: bool = True


async def active_work(session: AsyncSession) -> list[QueuedWork]:
    """Read every active generation run with its transport and timing metadata."""
    model = GenerationRunModel
    result = await session.scalars(
        select(model)
        .where(model.status.in_(ACTIVE_STATUSES))
        .order_by(model.created_at, model.id)
    )
    return [_queued_work(row) for row in result.all()]


def _queued_work(row: GenerationRunModel) -> QueuedWork:
    return QueuedWork(
        id=str(row.id),
        autopilot_run_id=row.autopilot_run_id,
        created_at=row.created_at,
        status=row.status,
        priority=priority_of(row.payload or {}),
        pgq_job_id=row.pgq_job_id,
        started_at=row.started_at,
        next_attempt_at=row.next_attempt_at,
    )


async def recent_drive_minutes(session: AsyncSession, limit: int) -> list[float]:
    """How long the latest finished autopilot drives took, newest first."""
    model = GenerationRunModel
    result = await session.execute(
        select(model.started_at, model.finished_at)
        .where(
            model.kind == KIND_AUTOPILOT_DRIVE,
            model.status == STATUS_SUCCEEDED,
            model.started_at.is_not(None),
            model.finished_at.is_not(None),
        )
        .order_by(model.finished_at.desc())
        .limit(limit)
    )
    return [
        (finished - started).total_seconds() / _SECONDS_PER_MINUTE
        for started, finished in result.all()
    ]


async def requeue_autopilot_dead_letter(
    session: AsyncSession, autopilot_run_id: str
) -> bool:
    """Requeue the latest parked run unless another active run owns its key."""
    row = await _latest_dead(session, autopilot_run_id)
    if row is None:
        return False
    return await _requeue_row(session, row)


async def _latest_dead(
    session: AsyncSession, autopilot_run_id: str
) -> GenerationRunModel | None:
    model = GenerationRunModel
    result = await session.execute(
        select(model)
        .where(
            model.autopilot_run_id == autopilot_run_id,
            model.status == STATUS_DEAD_LETTER,
        )
        .order_by(model.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def requeue_dead_letter(session: AsyncSession, run_id: UUID) -> bool:
    """Requeue one dead generation row in the caller's transaction; no commit."""
    row = await session.get(GenerationRunModel, run_id, populate_existing=True)
    if row is None:
        return False
    return await _requeue_row(session, row)


async def _requeue_row(session: AsyncSession, row: GenerationRunModel) -> bool:
    dead = run_from_row(row)
    counts = budget.reset_phase(dead.counts, dead.last_phase)
    try:
        async with session.begin_nested():
            result = await session.execute(_requeue_update(dead, counts))
    except IntegrityError:
        return False
    return cast(CursorResult[object], result).rowcount == 1


def _requeue_update(dead: GenerationRun, counts: AttemptCounts) -> Update:
    model = GenerationRunModel
    return (
        update(model)
        .where(model.id == dead.id, model.status == STATUS_DEAD_LETTER)
        .values(
            status=STATUS_QUEUED,
            created_at=UTC_CLOCK.now(),
            pgq_job_id=None,
            attempts=counts.attempts,
            phase_attempts=dict(counts.phase_attempts),
            finished_at=None,
            next_attempt_at=None,
        )
    )


__all__ = [
    "QueuedWork",
    "active_work",
    "recent_drive_minutes",
    "requeue_autopilot_dead_letter",
    "requeue_dead_letter",
]
