"""Public facade of the generation queue bounded context.

Cross-module code imports only these symbols (also re-exported from the package
``__init__``). The worker entry (``rag_backend.worker``) composes the rest.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Collection
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
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
from rag_backend.modules.generation_queue.constants import LOG_ORPHAN_ADOPTED
from rag_backend.modules.generation_queue.domain.clock import UTC_CLOCK
from rag_backend.modules.generation_queue.domain.errors import DriveLockBusyError
from rag_backend.modules.generation_queue.domain.models import (
    WorkflowResumePayload,
    adopt_stage,
    resume_stage,
)
from rag_backend.modules.generation_queue.infrastructure.drive_lock import (
    DriveLockTiming,
    PostgresDriveLock,
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
    from rag_backend.modules.generation_queue.infrastructure.rollback import (
        RollbackReport,
    )

logger = structlog.get_logger()

__all__ = [
    "QueueSchemaReport",
    "WorkflowResumePayload",
    "adopt_orphaned_projects",
    "apply_queue_schema",
    "count_queue_hand_back",
    "format_queue_schema_report",
    "hand_back_queue",
    "hold_project_drive",
    "listen_for_progress",
    "projects_with_active_runs",
    "queue_health_check",
    "register_persistence_models",
    "run_queue_monitor",
    "stage_workflow_resume",
    "verify_queue_schema",
]


async def stage_workflow_resume(
    session: AsyncSession, payload: WorkflowResumePayload, lock_version: int
) -> bool:
    """Queue a dashboard resume in the caller's transaction. The caller commits."""
    return await stage_generation_run(session, resume_stage(payload, lock_version))


def register_persistence_models() -> tuple[str, ...]:
    """Import the ORM model so its table attaches to ``Base.metadata``."""
    from rag_backend.modules.generation_queue.infrastructure.models import (
        GenerationRunModel,
    )

    return (GenerationRunModel.__tablename__,)


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
