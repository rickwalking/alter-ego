"""Public facade of the generation queue bounded context."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Collection
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import ColumnElement, exists, select
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.modules.generation_queue.application.executors import project_key
from rag_backend.modules.generation_queue.application.manual_reprocess import (
    ManualRecoveryDependencies,
    ManualRecoveryService,
)
from rag_backend.modules.generation_queue.constants import (
    LOG_ORPHAN_ADOPTED,
    ORPHAN_JOB_GRACE_SECONDS,
)
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.domain.errors import DriveLockBusyError
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    RecoveryCapability,
    RecoveryOutcome,
    RecoveryPolicy,
    RecoveryResult,
)
from rag_backend.modules.generation_queue.domain.manual_recovery_ports import (
    MaintenanceNotifier,
)
from rag_backend.modules.generation_queue.domain.models import (
    WorkflowResumePayload,
    adopt_stage,
    resume_stage,
)
from rag_backend.modules.generation_queue.domain.recovery import ParkedDrive
from rag_backend.modules.generation_queue.infrastructure.drive_lock import (
    DriveLockTiming,
    PostgresDriveLock,
)
from rag_backend.modules.generation_queue.infrastructure.maintenance_gateway import (
    WebMaintenanceGateway,
)
from rag_backend.modules.generation_queue.infrastructure.schema import (
    QueueSchemaReport,
)
from rag_backend.modules.generation_queue.infrastructure.schema import (
    apply as apply_queue_schema,
)
from rag_backend.modules.generation_queue.infrastructure.schema import (
    format_report as format_queue_schema_report,
)
from rag_backend.modules.generation_queue.infrastructure.schema import (
    verify as verify_queue_schema,
)
from rag_backend.modules.generation_queue.infrastructure.staging import (
    stage_generation_run,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_service import (
        EditorialWorkflowService,
    )
    from rag_backend.modules.generation_queue.infrastructure.queue_board import (
        BoardRow,
        RunFacts,
    )
    from rag_backend.modules.generation_queue.infrastructure.queue_view import (
        QueuedWork,
    )
    from rag_backend.modules.generation_queue.infrastructure.rollback import (
        RollbackReport,
    )

logger = structlog.get_logger()

__all__ = [
    "MaintenanceNotifier",
    "ManualRecoveryService",
    "ManualReprocessCommand",
    "ParkedDrive",
    "QueueSchemaReport",
    "RecoveryCapability",
    "RecoveryOutcome",
    "RecoveryResult",
    "WorkflowResumePayload",
    "active_queue",
    "adopt_orphaned_projects",
    "apply_queue_schema",
    "build_manual_recovery",
    "cancel_queued_run",
    "count_queue_hand_back",
    "format_queue_schema_report",
    "generation_run_facts",
    "hand_back_queue",
    "hold_project_drive",
    "listen_for_progress",
    "mark_recovery_attempt",
    "project_has_active_run",
    "projects_with_active_runs",
    "queue_board_rows",
    "queue_health_check",
    "recent_drive_minutes",
    "register_persistence_models",
    "requeue_autopilot_dead_letter",
    "run_queue_monitor",
    "stage_workflow_resume",
    "verify_queue_schema",
]


def build_manual_recovery(
    session: AsyncSession,
    notifier: MaintenanceNotifier | None = None,
    *,
    owns_transaction: bool = True,
) -> ManualRecoveryService:
    """Compose recovery with explicit transaction ownership on one session."""
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.modules.generation_queue.infrastructure import (
        manual_recovery_audit,
        manual_recovery_store,
    )

    bind = session.bind
    engine = bind.engine if isinstance(bind, AsyncConnection) else bind
    return ManualRecoveryService(
        ManualRecoveryDependencies(
            store=manual_recovery_store.SqlManualRecoveryStore(session, UTC_CLOCK),
            audit=manual_recovery_audit.SqlManualRecoveryAudit(session),
            lock=PostgresDriveLock(engine, _NO_WAIT),
            notifier=notifier or WebMaintenanceGateway(engine),
            clock=UTC_CLOCK,
            policy=RecoveryPolicy(
                heartbeat_stale_seconds=get_settings().workflow_run_heartbeat_stale_seconds,
                dispatcher_grace_seconds=ORPHAN_JOB_GRACE_SECONDS,
            ),
        ),
        owns_transaction=owns_transaction,
    )


async def stage_workflow_resume(
    session: AsyncSession, payload: WorkflowResumePayload, lock_version: int
) -> bool:
    """Queue a dashboard resume in the caller's transaction. The caller commits."""
    return await stage_generation_run(session, resume_stage(payload, lock_version))


def register_persistence_models() -> tuple[str, ...]:
    """Import the ORM model so its table attaches to ``Base.metadata``."""
    from rag_backend.modules.generation_queue.infrastructure.models import (
        CarouselGenerationEventModel,
        GenerationRunModel,
    )

    return (
        GenerationRunModel.__tablename__,
        CarouselGenerationEventModel.__tablename__,
    )


async def listen_for_progress(
    engine: AsyncEngine,
    engine_factory: Callable[[], EditorialWorkflowService],
    stop: asyncio.Event,
) -> None:
    """Web side of the progress relay: LISTEN until ``stop`` is set."""
    from rag_backend.modules.generation_queue.infrastructure.progress_relay import (
        ProgressRelayListener,
        gate_refetch,
    )

    listener = ProgressRelayListener(engine, gate_refetch(engine_factory))
    await listener.run(stop)


_NO_WAIT = DriveLockTiming(wait_seconds=0)


@asynccontextmanager
async def hold_project_drive(
    session: AsyncSession, project_id: str
) -> AsyncIterator[None]:
    """Drive a project from the web (the synchronous dashboard start).

    Takes the same drive lock as the worker, without waiting: when the worker
    (or another request) is driving the project, the caller gets the typed
    ``mutation_in_progress`` conflict (409) instead of a second driver.
    """
    bind = session.bind
    engine = bind.engine if isinstance(bind, AsyncConnection) else bind
    try:
        async with PostgresDriveLock(engine, _NO_WAIT).hold([project_key(project_id)]):
            yield
    except DriveLockBusyError:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
        ) from None


async def adopt_orphaned_projects(engine: AsyncEngine) -> int:
    """Queue a recovery for every project left ``in_progress`` with no run.

    Runs in the deploy one-shot, with the stack down. A project whose drive lock
    is held (someone is driving it) is skipped, so a run on a live stack never
    takes over a running drive. Returns how many recoveries were queued.
    """
    from rag_backend.modules.generation_queue.infrastructure.cutover import (
        orphaned_projects,
    )

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        orphans = await orphaned_projects(session)
    adopted = 0
    for project_id, title in orphans:
        try:
            async with (
                PostgresDriveLock(engine, _NO_WAIT).hold([project_key(project_id)]),
                sessions() as session,
            ):
                adopted += int(
                    await stage_generation_run(session, adopt_stage(project_id, title))
                )
                await session.commit()
        except DriveLockBusyError:
            continue
        logger.info(LOG_ORPHAN_ADOPTED, project_id=project_id)
    return adopted


def project_has_active_run(project_id: ColumnElement[str]) -> ColumnElement[bool]:
    """SQL ``EXISTS`` an active generation run for ``project_id`` (a column).

    Lets a writer fence its own UPDATE on the queue's ownership atomically
    (``WHERE NOT project_has_active_run(...)``), not only with a read before it.
    """
    from rag_backend.modules.generation_queue.constants import ACTIVE_STATUSES
    from rag_backend.modules.generation_queue.infrastructure.models import (
        GenerationRunModel,
    )

    return exists(
        select(GenerationRunModel.id).where(
            GenerationRunModel.carousel_project_id == project_id,
            GenerationRunModel.status.in_(ACTIVE_STATUSES),
        )
    )


async def projects_with_active_runs(
    session: AsyncSession, project_ids: Collection[str]
) -> set[str]:
    """The projects among ``project_ids`` with a queued, waiting or running run.

    The queue owns those projects: a dashboard resume waiting behind another job
    leaves its project ``in_progress`` with no heartbeat until the worker picks it
    up, and a job whose driver died is recovered by its own re-pick. The stale-run
    reaper leaves them alone.
    """
    if not project_ids:
        return set()
    from rag_backend.modules.generation_queue.constants import ACTIVE_STATUSES
    from rag_backend.modules.generation_queue.infrastructure.models import (
        GenerationRunModel,
    )

    rows = await session.scalars(
        select(GenerationRunModel.carousel_project_id)
        .where(
            GenerationRunModel.status.in_(ACTIVE_STATUSES),
            GenerationRunModel.carousel_project_id.in_(list(project_ids)),
        )
        .distinct()
    )
    return {str(project_id) for project_id in rows.all()}


async def queue_health_check(engine: AsyncEngine) -> dict[str, str | int]:
    """The ``/health/ready`` entry of the generation queue."""
    from rag_backend.modules.generation_queue.infrastructure.metrics import (
        read_queue_metrics,
    )

    return (await read_queue_metrics(engine, UTC_CLOCK.now())).as_check()


async def run_queue_monitor(
    engine: AsyncEngine, alert: Callable[[str], None], stop: asyncio.Event
) -> None:
    """Alert Pedro when the worker is gone 10 min or the queue stalls 6 h."""
    from rag_backend.modules.generation_queue.application.monitor import (
        MonitorDependencies,
        run_monitor,
    )
    from rag_backend.modules.generation_queue.infrastructure.metrics import (
        read_queue_metrics,
    )

    await run_monitor(
        MonitorDependencies(
            read=lambda: read_queue_metrics(engine, UTC_CLOCK.now()),
            alert=alert,
            clock=UTC_CLOCK,
        ),
        stop,
    )


async def hand_back_queue(engine: AsyncEngine) -> RollbackReport:
    """Before a revert: release unstarted resumes, cancel every active run."""
    from rag_backend.modules.generation_queue.infrastructure.rollback import hand_back

    return await hand_back(engine)


async def count_queue_hand_back(engine: AsyncEngine) -> RollbackReport:
    """What ``hand_back_queue`` would release and cancel (no change)."""
    from rag_backend.modules.generation_queue.infrastructure.rollback import pending

    return await pending(engine)


async def active_queue(session: AsyncSession) -> list[QueuedWork]:
    """The active generation runs in FIFO order, on the caller's session."""
    from rag_backend.modules.generation_queue.infrastructure.queue_view import (
        active_work,
    )

    return await active_work(session)


async def recent_drive_minutes(session: AsyncSession, limit: int) -> list[float]:
    """Minutes the latest finished autopilot drives took, newest first."""
    from rag_backend.modules.generation_queue.infrastructure import queue_view

    return await queue_view.recent_drive_minutes(session, limit)


async def mark_recovery_attempt(session: AsyncSession, generation_run_id: UUID) -> bool:
    """Mark a daily recovery attempt in the caller's transaction."""
    from rag_backend.modules.generation_queue.infrastructure.recovery_store import (
        mark_recovery_attempt as mark,
    )

    return await mark(session, generation_run_id)


async def requeue_autopilot_dead_letter(
    session: AsyncSession, autopilot_run_id: str
) -> bool:
    """Requeue the run's latest dead letter in the caller's transaction."""
    from rag_backend.modules.generation_queue.infrastructure import queue_view

    return await queue_view.requeue_autopilot_dead_letter(session, autopilot_run_id)


async def queue_board_rows(session: AsyncSession) -> list[BoardRow]:
    """Active runs in FIFO order, then the dead letters of the last 7 days."""
    from rag_backend.modules.generation_queue.infrastructure.queue_board import (
        board_rows,
    )

    return await board_rows(session)


async def generation_run_facts(session: AsyncSession, run_id: UUID) -> RunFacts | None:
    """Kind, status and autopilot run of one generation run."""
    from rag_backend.modules.generation_queue.infrastructure.queue_board import (
        run_facts,
    )

    return await run_facts(session, run_id)


async def cancel_queued_run(session: AsyncSession, run_id: UUID) -> bool:
    """Cancel a queued or retry-waiting run in the caller's transaction."""
    from rag_backend.modules.generation_queue.infrastructure.queue_board import (
        cancel_queued,
    )

    return await cancel_queued(session, run_id)
