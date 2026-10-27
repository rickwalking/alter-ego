"""Composition of the generation worker: handler, executors, dispatcher.

The worker entry (``rag_backend.worker.main``) owns the process: settings,
database, checkpointer, PgQueuer. This module only wires the queue's own parts
onto what it is given.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pgqueuer.adapters.persistence.queries import Queries
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.infrastructure.database.carousel_run_reaper import (
    CarouselRunReaperRepository,
)
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.generation_queue.application.dispatcher import (
    Dispatcher,
    DispatcherDependencies,
)
from rag_backend.modules.generation_queue.application.executors import (
    AutopilotDriveDependencies,
    AutopilotDriveExecutor,
    RecoveryDependencies,
    WorkflowResumeDependencies,
    WorkflowResumeExecutor,
)
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
)
from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    DailyScanDependencies,
)
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.domain.errors import ProviderClassifier
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.domain.ports import KindExecutor
from rag_backend.modules.generation_queue.domain.recovery import (
    ParkedDrive,
    RecoveryStore,
)
from rag_backend.modules.generation_queue.infrastructure.completion import (
    SseGenerationRunCompletion,
)
from rag_backend.modules.generation_queue.infrastructure.drive_adapters import (
    AutopilotStepperAdapter,
    EngineFactory,
    ProjectRecoveryAdapter,
    RecoveryConfig,
    WorkflowResumerAdapter,
)
from rag_backend.modules.generation_queue.infrastructure.drive_lock import (
    PostgresDriveLock,
)
from rag_backend.modules.generation_queue.infrastructure.generation_events import (
    SqlGenerationEventRecorder,
)
from rag_backend.modules.generation_queue.infrastructure.notices import (
    OwnerDeadLetterNotices,
)
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    PgQueuerJobQueue,
)
from rag_backend.modules.generation_queue.infrastructure.recovery_store import (
    SqlRecoveryStore,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)


class _NoAutopilot:
    """``AUTOPILOT_ENABLED=false``: the dispatcher stages no autopilot run."""

    @staticmethod
    async def active_run_ids(limit: int) -> list[tuple[str, str | None]]:
        """No run needs driving."""
        del limit
        return []


@dataclass(frozen=True, kw_only=True)
class HandlerParts:
    """What the job handler runs on."""

    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    bridge: AutopilotQueueBridge
    reaper: CarouselRunReaperRepository
    engine_factory: EngineFactory
    is_provider_error: ProviderClassifier
    stopping: Callable[[], bool]
    drive_autopilot: bool = True


@dataclass(frozen=True, kw_only=True)
class WorkerComposition:
    """The job handler and the dispatcher of one worker process."""

    handler: GenerationJobHandler
    dispatcher: Dispatcher
    scan: DailyRecoveryScan


@dataclass(frozen=True, kw_only=True)
class _NoParkedAutopilot:
    """Autopilot driving is off: the scan marks but revives nothing."""

    store: RecoveryStore

    async def revive_dead_letter(self, drive: ParkedDrive) -> bool:
        """Consume the scan's one attempt without reviving."""
        await self.store.mark_attempted(drive.generation_run_id)
        return False

    @staticmethod
    async def revive_stale(since: datetime) -> int:
        """Nothing to resume."""
        del since
        return 0


def compose_handler(parts: HandlerParts) -> GenerationJobHandler:
    """Wire the job handler and both executors."""
    store = SqlGenerationRunStore(parts.sessions)
    notices = OwnerDeadLetterNotices(parts.bridge, parts.sessions)
    recovery = RecoveryDependencies(
        store=store,
        recovery=ProjectRecoveryAdapter(
            RecoveryConfig(
                sessions=parts.sessions,
                reaper=parts.reaper,
                engine_factory=parts.engine_factory,
            )
        ),
    )
    executors: dict[GenerationKind, KindExecutor] = {
        GenerationKind.AUTOPILOT_DRIVE: AutopilotDriveExecutor(
            AutopilotDriveDependencies(
                stepper=AutopilotStepperAdapter(parts.bridge, parts.sessions),
                recovery=recovery,
                stopping=parts.stopping,
            )
        ),
        GenerationKind.WORKFLOW_RESUME: WorkflowResumeExecutor(
            WorkflowResumeDependencies(
                resumer=WorkflowResumerAdapter(parts.engine_factory),
                recovery=recovery,
            )
        ),
    }
    return GenerationJobHandler(
        HandlerDependencies(
            store=store,
            lock=PostgresDriveLock(parts.engine),
            executors=executors,
            notices=notices,
            clock=UTC_CLOCK,
            is_provider_error=parts.is_provider_error,
            events=SqlGenerationEventRecorder(parts.sessions),
            completion=SseGenerationRunCompletion(),
        )
    )


def compose_worker(parts: HandlerParts, queries: Queries) -> WorkerComposition:
    """The handler plus the dispatcher that feeds PgQueuer through ``queries``."""
    store = SqlGenerationRunStore(parts.sessions)
    dispatcher = Dispatcher(
        DispatcherDependencies(
            store=store,
            queue=PgQueuerJobQueue(queries),
            autopilot=parts.bridge if parts.drive_autopilot else _NoAutopilot(),
            notices=OwnerDeadLetterNotices(parts.bridge, parts.sessions),
            events=SqlGenerationEventRecorder(parts.sessions),
            completion=SseGenerationRunCompletion(),
        )
    )
    recovery_store = SqlRecoveryStore(parts.sessions)
    parked_autopilot = (
        parts.bridge
        if parts.drive_autopilot
        else _NoParkedAutopilot(store=recovery_store)
    )
    scan = DailyRecoveryScan(
        DailyScanDependencies(
            store=recovery_store, autopilot=parked_autopilot, clock=UTC_CLOCK
        )
    )
    return WorkerComposition(
        handler=compose_handler(parts), dispatcher=dispatcher, scan=scan
    )


__all__ = ["HandlerParts", "WorkerComposition", "compose_handler", "compose_worker"]
