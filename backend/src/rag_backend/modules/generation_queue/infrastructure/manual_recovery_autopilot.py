"""Existing autopilot revive/CAS and durable manual replacement staging."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.run_revive import (
    ReviveDependencies,
    revive,
)
from rag_backend.modules.autopilot.infrastructure.dead_letter_runs import (
    SqlDeadLetterRuns,
)
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.queue_constants import REASON_DEAD_RETRY
from rag_backend.modules.generation_queue.constants import (
    PAYLOAD_MANUAL_REPLACES_RUN_ID,
    STATUS_QUEUED,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    RecoveryMutation,
    RecoveryWrite,
    WriteStatus,
    manual_payload,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationRun,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.domain.ports import Clock
from rag_backend.modules.generation_queue.infrastructure.manual_recovery_cas import (
    RecoveryRunCAS,
    recovery_run_cas,
)
from rag_backend.modules.generation_queue.infrastructure.manual_recovery_reader import (
    ManualRecoveryReader,
)
from rag_backend.modules.generation_queue.infrastructure.staging import (
    stage_generation_run,
)


@dataclass(frozen=True, kw_only=True)
class _Successor:
    mutation: RecoveryMutation
    original: GenerationRun
    queued_id: UUID
    lock_version: int | None


class ManualRecoveryAutopilot:
    """Recover a dead autopilot row inside the caller's transaction."""

    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        reader: ManualRecoveryReader,
    ) -> None:
        self._session = session
        self._clock = clock
        self._reader = reader

    async def recover(
        self,
        mutation: RecoveryMutation,
        run: GenerationRun,
        lock_version: int | None,
    ) -> RecoveryWrite:
        """Revive through the existing CAS, then mark or stage the manual run."""
        if run.autopilot_run_id is None:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        autopilot_id = UUID(run.autopilot_run_id)
        autopilot = await SqlAlchemyAutopilotRepository(self._session).get(autopilot_id)
        if autopilot is None:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        queued_id = await revive(self._dependencies(), autopilot, REASON_DEAD_RETRY)
        if queued_id is None:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        if queued_id == autopilot_id:
            return await self._mark_requeued(mutation, run, lock_version)
        return await self._stage_successor(
            _Successor(
                mutation=mutation,
                original=run,
                queued_id=queued_id,
                lock_version=lock_version,
            )
        )

    def _dependencies(self) -> ReviveDependencies:
        return ReviveDependencies(
            runs=SqlAlchemyAutopilotRepository(self._session),
            clock=self._clock,
            queue=SqlQueueControl(self._session),
            dead_letters=SqlDeadLetterRuns(self._session),
        )

    async def _mark_requeued(
        self,
        mutation: RecoveryMutation,
        run: GenerationRun,
        lock_version: int | None,
    ) -> RecoveryWrite:
        updated = await recovery_run_cas(self._session, _metadata_cas(mutation, run))
        return RecoveryWrite(
            status=WriteStatus.APPLIED if updated is not None else WriteStatus.CONFLICT,
            run=updated,
            lock_version=lock_version,
        )

    async def _stage_successor(self, successor: _Successor) -> RecoveryWrite:
        mutation = successor.mutation
        project = mutation.snapshot.project
        stage = autopilot_stage(
            str(successor.queued_id), project.id if project is not None else None
        )
        payload = {
            **stage.payload,
            **manual_payload(mutation),
            PAYLOAD_MANUAL_REPLACES_RUN_ID: str(successor.original.id),
        }
        command = replace(stage, payload=payload)
        staged = await stage_generation_run(self._session, command, self._clock)
        if not staged:
            return RecoveryWrite(status=WriteStatus.CONFLICT)
        run = await self._reader.active_by_dedupe(command.dedupe_key)
        return RecoveryWrite(
            status=WriteStatus.APPLIED if run is not None else WriteStatus.CONFLICT,
            run=run,
            lock_version=successor.lock_version,
        )


def _metadata_cas(mutation: RecoveryMutation, run: GenerationRun) -> RecoveryRunCAS:
    return RecoveryRunCAS(
        mutation=mutation,
        run=run,
        expected_status=STATUS_QUEUED,
        payload={**run.payload, **manual_payload(mutation)},
    )


__all__ = ["ManualRecoveryAutopilot"]
