"""``QueueControl`` on the webhook's session, through the generation queue facade.

The generation queue facade is imported inside the methods: that package imports
the autopilot queue bridge at load time, so a module-level import here would make
the two packages load each other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    AsyncSessionTransaction,
)

from rag_backend.modules.autopilot.domain.queue_position import (
    QueueEntry,
    QueueSnapshot,
)
from rag_backend.modules.autopilot.infrastructure.queue_waiting import (
    waiting_autopilot_runs,
    waiting_entry,
)
from rag_backend.modules.autopilot.queue_constants import (
    GENERATION_KIND_AUTOPILOT,
    LOG_OWNER_QUEUE_DISPATCH_FAILED,
    OUTCOME_ALREADY,
    OUTCOME_DONE,
    OUTCOME_NOT_ALLOWED,
    OUTCOME_NOT_FOUND,
    RECENT_DRIVES,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.application.manual_reprocess import (
        ManualRecoveryService,
    )
    from rag_backend.modules.generation_queue.domain.manual_recovery import (
        MaintenanceNotice,
        ManualReprocessCommand,
        RecoveryResult,
    )
    from rag_backend.modules.generation_queue.domain.manual_recovery_ports import (
        MaintenanceNotifier,
    )
    from rag_backend.modules.generation_queue.infrastructure.queue_view import (
        QueuedWork,
    )


logger = structlog.get_logger()


class SqlQueueControl:
    """Bind queue reads and shared recovery to one request session."""

    def __init__(
        self,
        session: AsyncSession,
        notifier: MaintenanceNotifier | None = None,
        *,
        deferred: bool = False,
    ) -> None:
        self._session = session
        self._notifier = notifier
        self._deferred = deferred
        self._pending_notices: list[MaintenanceNotice] = []

    async def snapshot(self) -> QueueSnapshot:
        """Read active and driven runs, excluding POV runs without a thesis."""
        from rag_backend.modules.generation_queue.public import (
            active_queue,
            recent_drive_minutes,
        )

        active = await active_queue(self._session)
        active_entries = tuple(_active_entry(work) for work in active)
        ahead = tuple(entry.autopilot_run_id for entry in active_entries)
        staged = {run_id for run_id in ahead if run_id is not None}
        driven = await waiting_autopilot_runs(self._session)
        waiting = tuple(run for run in driven if run.id not in staged)
        drives = await recent_drive_minutes(self._session, RECENT_DRIVES)
        return QueueSnapshot(
            entries=(*active_entries, *(waiting_entry(run) for run in waiting)),
            ahead=ahead,
            waiting=tuple(run.id for run in waiting),
            drive_minutes=tuple(drives),
        )

    async def reprocess_autopilot(self, run_id: UUID, actor_id: str) -> UUID | None:
        """Delegate Telegram retry to shared manual recovery semantics."""
        from rag_backend.modules.generation_queue.domain.manual_recovery import (
            ManualReprocessCommand,
            RecoveryOutcome,
        )

        command = ManualReprocessCommand(
            project_id=None, run_id=None, autopilot_run_id=run_id, actor_id=actor_id
        )
        result = await self._recover(command)
        if result.outcome is not RecoveryOutcome.QUEUED or result.run is None:
            return None
        queued = result.run.autopilot_run_id
        return UUID(queued) if queued is not None else None

    async def retry_generation(self, run_id: UUID, actor_id: str) -> str:
        """Preserve the panel outcome contract around shared manual recovery."""
        from rag_backend.modules.generation_queue.domain.manual_recovery import (
            ManualReprocessCommand,
        )
        from rag_backend.modules.generation_queue.public import generation_run_facts

        facts = await generation_run_facts(self._session, run_id)
        if facts is None:
            return OUTCOME_NOT_FOUND
        if facts.kind != GENERATION_KIND_AUTOPILOT:
            return OUTCOME_NOT_ALLOWED
        command = ManualReprocessCommand(
            project_id=None, run_id=run_id, actor_id=actor_id
        )
        return _retry_outcome(await self._recover(command))

    async def _recover(self, command: ManualReprocessCommand) -> RecoveryResult:
        if not self._deferred:
            return await self._recovery_service(deferred=False).reprocess(command)
        savepoint = await self._session.begin_nested()
        try:
            result = await self._recovery_service(deferred=True).reprocess(command)
        except Exception:
            await self._rollback_deferred(savepoint)
            raise
        return await self._finish_deferred(savepoint, result)

    def _recovery_service(self, *, deferred: bool) -> ManualRecoveryService:
        from rag_backend.modules.generation_queue.public import build_manual_recovery

        notifier = self if deferred else self._notifier
        return build_manual_recovery(
            self._session, notifier, owns_transaction=not deferred
        )

    async def _finish_deferred(
        self, savepoint: AsyncSessionTransaction, result: RecoveryResult
    ) -> RecoveryResult:
        from rag_backend.modules.generation_queue.domain.manual_recovery import (
            RecoveryOutcome,
        )

        if result.outcome in {RecoveryOutcome.REFUSED, RecoveryOutcome.NOT_FOUND}:
            await self._rollback_deferred(savepoint)
            return result
        await savepoint.commit()
        return result

    async def _rollback_deferred(self, savepoint: AsyncSessionTransaction) -> None:
        await savepoint.rollback()
        self._pending_notices.clear()

    async def notify(self, notice: MaintenanceNotice) -> bool:
        """Buffer a dispatch notice until the webhook commits."""
        self._pending_notices.append(notice)
        return True

    async def deliver_notifications(self) -> None:
        """Publish buffered dispatch notices after the outer commit."""
        notices = tuple(self._pending_notices)
        self._pending_notices.clear()
        notifier = self._default_notifier()
        for notice in notices:
            try:
                await notifier.notify(notice)
            except Exception as exc:
                logger.warning(
                    LOG_OWNER_QUEUE_DISPATCH_FAILED,
                    error_type=type(exc).__name__,
                )

    def discard_notifications(self) -> None:
        """Drop buffered notices when the outer transaction rolls back."""
        self._pending_notices.clear()

    def _default_notifier(self) -> MaintenanceNotifier:
        if self._notifier is not None:
            return self._notifier
        from rag_backend.modules.generation_queue import WebMaintenanceGateway

        bind = self._session.bind
        engine = bind.engine if isinstance(bind, AsyncConnection) else bind
        return WebMaintenanceGateway(engine)

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Requeue the run's latest dead letter in this transaction."""
        from rag_backend.modules.generation_queue.public import (
            requeue_autopilot_dead_letter,
        )

        return await requeue_autopilot_dead_letter(self._session, str(run_id))


def _active_entry(work: QueuedWork) -> QueueEntry:
    return QueueEntry(
        id=work.id,
        status=work.status,
        autopilot_run_id=work.autopilot_run_id,
        created_at=work.created_at,
        pgq_job_id=work.pgq_job_id,
        priority=work.priority,
        started_at=work.started_at,
        next_attempt_at=work.next_attempt_at,
        staged=work.staged,
    )


def _retry_outcome(result: RecoveryResult) -> str:
    from rag_backend.modules.generation_queue.domain.manual_recovery import (
        RecoveryOutcome,
        RefusalCode,
    )

    if result.outcome is RecoveryOutcome.QUEUED:
        return OUTCOME_DONE
    if result.outcome is RecoveryOutcome.NOT_FOUND:
        return OUTCOME_NOT_FOUND
    if result.refusal is RefusalCode.UNSUPPORTED:
        return OUTCOME_NOT_ALLOWED
    return OUTCOME_ALREADY


__all__ = ["SqlQueueControl"]
