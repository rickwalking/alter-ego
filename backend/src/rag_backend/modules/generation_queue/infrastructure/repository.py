"""``generation_runs`` store for the worker: one short committed session per call.

Status changes are compare-and-set on the current status, so the handler, the
dispatcher and a future retry button can race without a lost update.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import ColumnElement, CursorResult, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    KIND_WORKFLOW_RESUME,
    STATUS_DEAD_LETTER,
    STATUS_QUEUED,
    STATUS_RETRY_WAIT,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain import budget
from rag_backend.modules.generation_queue.domain.models import (
    CountsUpdate,
    DeadLetterCommand,
    GenerationKind,
    GenerationRun,
    GenerationStatus,
    RetryCommand,
    StageCommand,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.staging import (
    stage_generation_run,
)

SessionFactory = async_sessionmaker[AsyncSession]


def run_from_row(row: GenerationRunModel) -> GenerationRun:
    """Map an ORM row to the domain run."""
    return GenerationRun(
        id=row.id,
        kind=GenerationKind(row.kind),
        dedupe_key=row.dedupe_key,
        status=GenerationStatus(row.status),
        payload=dict(row.payload or {}),
        autopilot_run_id=row.autopilot_run_id,
        carousel_project_id=row.carousel_project_id,
        pgq_job_id=row.pgq_job_id,
        attempts=int(row.attempts or 0),
        phase_attempts={str(k): int(v) for k, v in (row.phase_attempts or {}).items()},
        last_phase=row.last_phase,
        last_error_code=row.last_error_code,
        created_at=row.created_at,
    )


def _active() -> ColumnElement[bool]:
    return GenerationRunModel.status.in_(ACTIVE_STATUSES)


class SqlGenerationRunStore:
    """Implements ``GenerationRunStore`` on its own sessions."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def get(self, run_id: UUID) -> GenerationRun | None:
        """The run, or None."""
        async with self._sessions() as session:
            row = await session.get(GenerationRunModel, run_id)
            return run_from_row(row) if row is not None else None

    async def stage(self, command: StageCommand) -> bool:
        """Stage in a session of its own (the dispatcher's safety net)."""
        async with self._sessions() as session:
            inserted = await stage_generation_run(session, command)
            await session.commit()
            return inserted

    async def undispatched(self, limit: int) -> list[GenerationRun]:
        """Queued runs with no job yet, oldest first (FIFO hand-over)."""
        return await self._list(
            (
                GenerationRunModel.status == STATUS_QUEUED,
                GenerationRunModel.pgq_job_id.is_(None),
            ),
            limit,
        )

    async def dispatched_active(self, limit: int) -> list[GenerationRun]:
        """Active runs that carry a job id, oldest first."""
        return await self._list(
            (_active(), GenerationRunModel.pgq_job_id.is_not(None)), limit
        )

    async def _list(
        self, conditions: Sequence[ColumnElement[bool]], limit: int
    ) -> list[GenerationRun]:
        async with self._sessions() as session:
            result = await session.execute(
                select(GenerationRunModel)
                .where(*conditions)
                .order_by(GenerationRunModel.created_at, GenerationRunModel.id)
                .limit(limit)
            )
            return [run_from_row(row) for row in result.scalars().all()]

    async def set_job(self, run_id: UUID, job_id: int) -> None:
        """Record the job carrying the run."""
        await self._update(run_id, {"pgq_job_id": job_id})

    async def clear_job(self, run_id: UUID) -> None:
        """Forget a lost job while the run is still active; queue it again.

        A run that finished between the dispatcher's two reads keeps its status.
        """
        await self._cas(
            run_id, ACTIVE_STATUSES, {"pgq_job_id": None, "status": STATUS_QUEUED}
        )

    async def mark_running(self, run_id: UUID) -> bool:
        """Active → running."""
        return await self._cas(
            run_id,
            ACTIVE_STATUSES,
            {"status": STATUS_RUNNING, "started_at": _now(), "next_attempt_at": None},
        )

    async def save_counts(self, run_id: UUID, update_: CountsUpdate) -> None:
        """Persist the attempt counters and the phase they were counted for."""
        await self._update(
            run_id,
            {
                "attempts": update_.counts.attempts,
                "phase_attempts": dict(update_.counts.phase_attempts),
                "last_phase": update_.phase,
            },
        )

    async def mark_succeeded(self, run_id: UUID) -> None:
        """Running → succeeded."""
        await self._cas(
            run_id,
            (STATUS_RUNNING,),
            {"status": STATUS_SUCCEEDED, "finished_at": _now()},
        )

    async def mark_waiting(self, command: RetryCommand) -> None:
        """Running → retry_wait until the next attempt."""
        await self._cas(
            command.run_id,
            (STATUS_RUNNING,),
            {
                "status": STATUS_RETRY_WAIT,
                "next_attempt_at": command.next_attempt_at,
                "last_error_code": command.error_code,
                "last_error": command.error or None,
            },
        )

    async def mark_dead_letter(self, command: DeadLetterCommand) -> bool:
        """Active → dead_letter with the classified reason."""
        return await self._cas(
            command.run_id,
            ACTIVE_STATUSES,
            {
                "status": STATUS_DEAD_LETTER,
                "finished_at": _now(),
                "last_error_code": command.error_code,
                "last_error": command.error,
            },
        )

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Dead letter → queued once; only the failing phase's starts are forgotten.

        Refused (False) while another run with the same dedupe key is active.
        """
        run = await self.get(run_id)
        if run is None or run.status is not GenerationStatus.DEAD_LETTER:
            return False
        counts = budget.reset_phase(run.counts, run.last_phase)
        try:
            return await self._requeue(run_id, counts)
        except IntegrityError:
            return False

    async def _requeue(self, run_id: UUID, counts: budget.AttemptCounts) -> bool:
        """The CAS; a newer active run with the same key makes it a unique error."""
        return await self._cas(
            run_id,
            (STATUS_DEAD_LETTER,),
            {
                "status": STATUS_QUEUED,
                "pgq_job_id": None,
                "attempts": counts.attempts,
                "phase_attempts": dict(counts.phase_attempts),
                "finished_at": None,
                "next_attempt_at": None,
            },
        )

    async def other_active_for_project(self, project_id: str, run_id: UUID) -> bool:
        """Another active dashboard resume targets the project."""
        async with self._sessions() as session:
            found = await session.scalar(
                select(GenerationRunModel.id)
                .where(
                    GenerationRunModel.carousel_project_id == project_id,
                    GenerationRunModel.kind == KIND_WORKFLOW_RESUME,
                    GenerationRunModel.id != run_id,
                    _active(),
                )
                .limit(1)
            )
            return found is not None

    async def _update(self, run_id: UUID, values: dict[str, object]) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(GenerationRunModel)
                .where(GenerationRunModel.id == run_id)
                .values(**values, updated_at=_now())
            )
            await session.commit()

    async def _cas(
        self, run_id: UUID, expected: Sequence[str], values: dict[str, object]
    ) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                update(GenerationRunModel)
                .where(
                    GenerationRunModel.id == run_id,
                    GenerationRunModel.status.in_(tuple(expected)),
                )
                .values(**values, updated_at=_now())
            )
            await session.commit()
            return cast(CursorResult[object], result).rowcount == 1


def _now() -> datetime:
    return datetime.now(UTC)


__all__ = ["SessionFactory", "SqlGenerationRunStore", "run_from_row"]
