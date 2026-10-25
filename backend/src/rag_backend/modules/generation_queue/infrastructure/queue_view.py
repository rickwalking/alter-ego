"""Read the queue order and requeue a parked autopilot drive, in the caller's session.

The Telegram webhook shows a run's queue position and retries a dead letter inside
its own transaction: the autopilot run's state change and the generation run's
requeue commit together, so the dispatcher never sees one without the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from sqlalchemy import CursorResult, select, update
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
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    run_from_row,
)

_SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True, kw_only=True)
class QueuedWork:
    """One active generation run, in queue order."""

    autopilot_run_id: str | None
    created_at: datetime


async def active_work(session: AsyncSession) -> list[QueuedWork]:
    """Queued, running and retry-waiting runs, oldest first (the FIFO order)."""
    model = GenerationRunModel
    result = await session.execute(
        select(model.autopilot_run_id, model.created_at)
        .where(model.status.in_(ACTIVE_STATUSES))
        .order_by(model.created_at, model.id)
    )
    return [
        QueuedWork(autopilot_run_id=row[0], created_at=row[1]) for row in result.all()
    ]


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
    """The run's latest dead letter → queued, failing phase reset; no commit.

    The run joins the back of the queue (``created_at`` is now): PgQueuer hands it
    a new job behind every job already handed over.

    False when the run has no dead letter, or another active run holds the same
    dedupe key (then that run carries the work).
    """
    model = GenerationRunModel
    row = (
        await session.execute(
            select(model)
            .where(
                model.autopilot_run_id == autopilot_run_id,
                model.status == STATUS_DEAD_LETTER,
            )
            .order_by(model.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    dead = run_from_row(row)
    counts = budget.reset_phase(dead.counts, dead.last_phase)
    try:
        async with session.begin_nested():
            result = await session.execute(
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
    except IntegrityError:
        return False
    return cast(CursorResult[object], result).rowcount == 1


__all__ = [
    "QueuedWork",
    "active_work",
    "recent_drive_minutes",
    "requeue_autopilot_dead_letter",
]
