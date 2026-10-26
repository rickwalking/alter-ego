"""Session-scoped manual recovery store with atomic CAS and successor identity."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.modules.autopilot.domain.queue_position import (
    QueuePosition,
    position_of,
)
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner
from rag_backend.modules.generation_queue.constants import (
    PAYLOAD_MANUAL_ACCELERATE_JOB_ID,
    PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID,
    PAYLOAD_MANUAL_CANCEL_JOB_ID,
    STATUS_QUEUED,
    STATUS_RETRY_WAIT,
    STATUS_RUNNING,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    RecoveryMutation,
    RecoverySnapshot,
    RecoveryWrite,
    StuckKind,
    WriteStatus,
    manual_payload,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
    adopt_stage,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.domain.ports import Clock
from rag_backend.modules.generation_queue.infrastructure import (
    manual_recovery_autopilot,
)
from rag_backend.modules.generation_queue.infrastructure.manual_recovery_cas import (
    RecoveryRunCAS,
    recovery_run_cas,
)
from rag_backend.modules.generation_queue.infrastructure.manual_recovery_reader import (
    ManualRecoveryReader,
)
from rag_backend.modules.generation_queue.infrastructure.queue_view import (
    requeue_dead_letter,
)
from rag_backend.modules.generation_queue.infrastructure.staging import (
    stage_generation_run,
)


@dataclass(frozen=True)
class _ProjectClaim:
    version: int | None
    moved: bool


class SqlManualRecoveryStore:
    """Implement the isolated manual store without owning the request session."""

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock
        self._reader = ManualRecoveryReader(session)
        self._autopilot = manual_recovery_autopilot.ManualRecoveryAutopilot(
            session, clock, self._reader
        )

    async def load(self, command: ManualReprocessCommand) -> RecoverySnapshot:
        """Load fresh target state."""
        return await self._reader.load(command)

    async def find_existing(self, snapshot: RecoverySnapshot) -> GenerationRun | None:
        """Find an active compatible manual original or successor before CAS."""
        return await self._reader.find_existing(snapshot)

    async def apply(self, mutation: RecoveryMutation) -> RecoveryWrite:
        """Serialize on the old run/project and apply one atomic recovery."""
        fresh = await self._reader.serialize(mutation.snapshot)
        existing = await self._reader.find_existing(fresh)
        if existing is not None:
            return RecoveryWrite(
                status=WriteStatus.EXISTING,
                run=existing,
                lock_version=_version(fresh),
            )
        claim = await self._claim_project(fresh)
        if not claim.moved:
            return await self._conflict(mutation, WriteStatus.STALE_VERSION)
        current = replace(mutation, snapshot=fresh)
        write = await self._route(current, claim.version)
        if write.status is not WriteStatus.CONFLICT:
            return write
        return await self._conflict(current)

    async def position(self, run: GenerationRun) -> QueuePosition | None:
        """Place one queued run with the shared scheduling core."""
        snapshot = await SqlQueueControl(self._session).snapshot()
        target = UUID(run.autopilot_run_id or str(run.id))
        return position_of(snapshot, target, self._clock.now())

    async def commit(self) -> None:
        """Commit recovery and audit together."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back a refused or losing request."""
        await self._session.rollback()

    async def _route(
        self, mutation: RecoveryMutation, lock_version: int | None
    ) -> RecoveryWrite:
        if mutation.stuck is StuckKind.ORPHAN:
            return await self._orphan(mutation, lock_version)
        run = mutation.snapshot.run
        if run is None:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        if mutation.stuck is StuckKind.DEAD_LETTER:
            return await self._dead(mutation, run, lock_version)
        if mutation.stuck is StuckKind.RETRY_WAIT:
            return await self._retry(mutation, run, lock_version)
        return await self._stale(mutation, run, lock_version)

    async def _dead(
        self,
        mutation: RecoveryMutation,
        run: GenerationRun,
        lock_version: int | None,
    ) -> RecoveryWrite:
        if run.kind is GenerationKind.AUTOPILOT_DRIVE:
            return await self._autopilot.recover(mutation, run, lock_version)
        requeued = await requeue_dead_letter(self._session, run.id)
        current = await self._reader.run_by_id(run.id)
        if not requeued or current is None:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        command = RecoveryRunCAS(
            mutation=mutation,
            run=current,
            expected_status=STATUS_QUEUED,
            payload={**current.payload, **manual_payload(mutation)},
        )
        updated = await recovery_run_cas(self._session, command)
        return _write(updated, lock_version)

    async def _retry(
        self,
        mutation: RecoveryMutation,
        run: GenerationRun,
        lock_version: int | None,
    ) -> RecoveryWrite:
        payload = {**run.payload, **manual_payload(mutation)}
        _transport_fence(payload, run, accelerate=True)
        command = RecoveryRunCAS(
            mutation=mutation,
            run=run,
            expected_status=STATUS_RETRY_WAIT,
            payload=payload,
        )
        updated = await recovery_run_cas(self._session, command)
        return _write(updated, lock_version)

    async def _stale(
        self,
        mutation: RecoveryMutation,
        run: GenerationRun,
        lock_version: int | None,
    ) -> RecoveryWrite:
        payload = {**run.payload, **manual_payload(mutation)}
        _transport_fence(payload, run, accelerate=False)
        command = RecoveryRunCAS(
            mutation=mutation,
            run=run,
            expected_status=STATUS_RUNNING,
            payload=payload,
        )
        updated = await recovery_run_cas(self._session, command)
        return _write(updated, lock_version)

    async def _orphan(
        self, mutation: RecoveryMutation, lock_version: int | None
    ) -> RecoveryWrite:
        project = mutation.snapshot.project
        if project is None:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        stage = (
            autopilot_stage(mutation.snapshot.autopilot_run_id, project.id)
            if mutation.snapshot.autopilot_run_id is not None
            else adopt_stage(project.id, project.title)
        )
        command = replace(stage, payload={**stage.payload, **manual_payload(mutation)})
        staged = await stage_generation_run(self._session, command, self._clock)
        if not staged:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        run = await self._reader.active_by_dedupe(command.dedupe_key)
        return _write(run, lock_version)

    async def _claim_project(self, snapshot: RecoverySnapshot) -> _ProjectClaim:
        project = snapshot.project
        expected = snapshot.command.expected_version
        if project is None:
            return _ProjectClaim(version=None, moved=True)
        if expected is None:
            return _ProjectClaim(version=project.lock_version, moved=True)
        try:
            bumped = await CarouselProjectWriteOwner(
                self._session
            ).bump_resume_lock_version(project.id, expected)
        except ValueError as exc:
            if str(exc) != ERR_VERSION_CONFLICT:
                raise
            return _ProjectClaim(version=None, moved=False)
        return _ProjectClaim(version=bumped, moved=True)

    async def _conflict(
        self, mutation: RecoveryMutation, fallback: WriteStatus = WriteStatus.CONFLICT
    ) -> RecoveryWrite:
        fresh = await self._reader.load(mutation.snapshot.command)
        existing = await self._reader.find_existing(fresh)
        if existing is not None:
            return RecoveryWrite(
                status=WriteStatus.EXISTING,
                run=existing,
                lock_version=_version(fresh),
            )
        return RecoveryWrite(status=fallback)


def _transport_fence(
    payload: dict[str, object], run: GenerationRun, *, accelerate: bool
) -> None:
    if run.pgq_job_id is None:
        return
    if accelerate:
        payload[PAYLOAD_MANUAL_ACCELERATE_JOB_ID] = run.pgq_job_id
    payload[PAYLOAD_MANUAL_CANCEL_JOB_ID] = run.pgq_job_id
    attempt_id = _old_attempt(run)
    if attempt_id is not None:
        payload[PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID] = str(attempt_id)


def _write(run: GenerationRun | None, lock_version: int | None) -> RecoveryWrite:
    return RecoveryWrite(
        status=WriteStatus.APPLIED if run is not None else WriteStatus.CONFLICT,
        run=run,
        lock_version=lock_version,
    )


def _version(snapshot: RecoverySnapshot) -> int | None:
    return snapshot.project.lock_version if snapshot.project is not None else None


def _old_attempt(run: GenerationRun) -> UUID | None:
    try:
        return run.attempt_id
    except ValueError:
        return None


__all__ = ["SqlManualRecoveryStore"]
