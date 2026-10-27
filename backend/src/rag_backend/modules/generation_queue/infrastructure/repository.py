"""``generation_runs`` store for the worker: one short committed session per call.

Status changes are compare-and-set on the current status, so the handler, the
dispatcher and a future retry button can race without a lost update.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, CursorResult, Text, func, select, true, update
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
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
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    AttemptDeadLetterCommand,
    CountsUpdate,
    DeadLetterCommand,
    GenerationKind,
    GenerationRun,
    GenerationStatus,
    RetryCommand,
    StageCommand,
)
from rag_backend.modules.generation_queue.domain.ports import Clock
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


async def _resolve_project(session: AsyncSession, run: GenerationRun) -> GenerationRun:
    if run.carousel_project_id is not None or run.autopilot_run_id is None:
        return run
    parent_id = _autopilot_uuid(run.autopilot_run_id)
    if parent_id is None:
        return run
    parent = await session.get(AutopilotRunModel, parent_id)
    if parent is None:
        return run
    return replace(run, carousel_project_id=parent.carousel_project_id)


def _autopilot_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _active() -> ColumnElement[bool]:
    return GenerationRunModel.status.in_(ACTIVE_STATUSES)


def _attempt_matches(attempt_id: UUID) -> ColumnElement[bool]:
    value = cast(
        ColumnElement[str],
        GenerationRunModel.payload[ATTEMPT_ID_KEY].as_string(),
    )
    return value == str(attempt_id)


def _attempt_payload(
    dialect: str, attempt_id: UUID
) -> ColumnElement[dict[str, object]]:
    if dialect == "postgresql":
        expression = func.jsonb_set(
            GenerationRunModel.payload,
            pg_array([ATTEMPT_ID_KEY], type_=Text),
            func.to_jsonb(str(attempt_id)),
            true(),
        )
    else:
        expression = func.json_set(
            GenerationRunModel.payload, "$." + ATTEMPT_ID_KEY, str(attempt_id)
        )
    return cast(ColumnElement[dict[str, object]], expression)


class SqlGenerationRunStore:
    """Implements ``GenerationRunStore`` on its own sessions."""

    def __init__(self, sessions: SessionFactory, clock: Clock = UTC_CLOCK) -> None:
        self._sessions = sessions
        self._clock = clock

    async def get(self, run_id: UUID) -> GenerationRun | None:
        """The run, or None."""
        async with self._sessions() as session:
            row = await session.get(GenerationRunModel, run_id)
            if row is None:
                return None
            return await _resolve_project(session, run_from_row(row))

    async def stage(self, command: StageCommand) -> bool:
        """Stage in a session of its own (the dispatcher's safety net)."""
        async with self._sessions() as session:
            inserted = await stage_generation_run(session, command, self._clock)
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
            return [
                await _resolve_project(session, run_from_row(row))
                for row in result.scalars().all()
            ]

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

    async def mark_running(self, run_id: UUID) -> UUID | None:
        """Active → running with a fresh UUID rotated into the payload."""
        attempt_id = uuid4()
        claimed = await self._claim(run_id, attempt_id)
        return attempt_id if claimed else None

    async def save_counts(
        self, run_id: UUID, attempt_id: UUID, update_: CountsUpdate
    ) -> bool:
        """Persist counters only for the expected running attempt."""
        return await self._attempt_cas(
            run_id,
            attempt_id,
            {
                "attempts": update_.counts.attempts,
                "phase_attempts": dict(update_.counts.phase_attempts),
                "last_phase": update_.phase,
            },
        )

    async def mark_succeeded(self, run_id: UUID, attempt_id: UUID) -> bool:
        """Running → succeeded only for the expected attempt."""
        return await self._attempt_cas(
            run_id,
            attempt_id,
            {"status": STATUS_SUCCEEDED, "finished_at": self._clock.now()},
        )

    async def mark_waiting(self, command: RetryCommand) -> bool:
        """Running → retry_wait only for the expected attempt."""
        return await self._attempt_cas(
            command.run_id,
            command.attempt_id,
            {
                "status": STATUS_RETRY_WAIT,
                "next_attempt_at": command.next_attempt_at,
                "last_error_code": command.error_code,
                "last_error": command.error or None,
            },
        )

    async def mark_attempt_dead_letter(self, command: AttemptDeadLetterCommand) -> bool:
        """Running → dead_letter only for the expected attempt."""
        return await self._attempt_cas(
            command.run_id,
            command.attempt_id,
            {
                "status": STATUS_DEAD_LETTER,
                "finished_at": self._clock.now(),
                "last_error_code": command.error_code,
                "last_error": command.error,
            },
        )

    async def mark_dead_letter(self, command: DeadLetterCommand) -> bool:
        """Active → dead_letter for the dispatcher's held-job path."""
        return await self._cas(
            command.run_id,
            ACTIVE_STATUSES,
            {
                "status": STATUS_DEAD_LETTER,
                "finished_at": self._clock.now(),
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

    async def _claim(self, run_id: UUID, attempt_id: UUID) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                update(GenerationRunModel)
                .where(GenerationRunModel.id == run_id, _active())
                .values(
                    status=STATUS_RUNNING,
                    started_at=self._clock.now(),
                    next_attempt_at=None,
                    payload=_attempt_payload(
                        session.get_bind().dialect.name, attempt_id
                    ),
                    updated_at=self._clock.now(),
                )
            )
            await session.commit()
            return cast(CursorResult[object], result).rowcount == 1

    async def _update(self, run_id: UUID, values: dict[str, object]) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(GenerationRunModel)
                .where(GenerationRunModel.id == run_id)
                .values(**values, updated_at=self._clock.now())
            )
            await session.commit()

    async def _cas(
        self, run_id: UUID, expected: Sequence[str], values: dict[str, object]
    ) -> bool:
        conditions = (
            GenerationRunModel.id == run_id,
            GenerationRunModel.status.in_(tuple(expected)),
        )
        return await self._cas_where(conditions, values)

    async def _attempt_cas(
        self, run_id: UUID, attempt_id: UUID, values: dict[str, object]
    ) -> bool:
        conditions = (
            GenerationRunModel.id == run_id,
            GenerationRunModel.status == STATUS_RUNNING,
            _attempt_matches(attempt_id),
        )
        return await self._cas_where(conditions, values)

    async def _cas_where(
        self,
        conditions: Sequence[ColumnElement[bool]],
        values: dict[str, object],
    ) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                update(GenerationRunModel)
                .where(*conditions)
                .values(**values, updated_at=self._clock.now())
            )
            await session.commit()
            return cast(CursorResult[object], result).rowcount == 1


__all__ = ["SessionFactory", "SqlGenerationRunStore", "run_from_row"]
