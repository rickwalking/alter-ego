"""PgQueuer adapter and composition for generation maintenance control."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pgqueuer import PgQueuer
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.models import Job
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.generation_queue.application.dispatcher import Dispatcher
from rag_backend.modules.generation_queue.application.maintenance import (
    MaintenanceDependencies,
    MaintenanceExecutor,
)
from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
)
from rag_backend.modules.generation_queue.constants import (
    MAINTENANCE_CONCURRENCY_LIMIT,
    MAINTENANCE_ENTRYPOINT,
)
from rag_backend.modules.generation_queue.infrastructure.maintenance_gateway import (
    PgQueuerMaintenanceGateway,
)
from rag_backend.modules.generation_queue.infrastructure.maintenance_lock import (
    PostgresMaintenanceLock,
)
from rag_backend.worker.recovery import (
    AlertSender,
    register_daily_scan,
    run_daily_scan,
)
from rag_backend.worker.schedules import (
    register_backlog_promotion,
    run_backlog_promotion,
)


@dataclass(frozen=True, kw_only=True)
class WorkerMaintenance:
    """The existing worker pieces used by control jobs and both cron schedules."""

    pgq: PgQueuer
    queries: Queries
    engine: AsyncEngine
    dispatcher: Dispatcher
    scan: DailyRecoveryScan
    bridge: AutopilotQueueBridge
    alert: AlertSender
    autopilot_enabled: bool


def maintenance_entrypoint(
    executor: MaintenanceExecutor,
) -> Callable[[Job], Awaitable[None]]:
    """Turn a durable control job into its bounded maintenance execution."""

    async def run(job: Job) -> None:
        await executor.execute(job.payload)

    return run


def register_maintenance(wiring: WorkerMaintenance) -> None:
    """Register the separate entrypoint and cron enqueue paths."""
    executor = _executor(wiring)
    wiring.pgq.entrypoint(
        MAINTENANCE_ENTRYPOINT,
        concurrency_limit=MAINTENANCE_CONCURRENCY_LIMIT,
    )(maintenance_entrypoint(executor))
    control = PgQueuerMaintenanceGateway(wiring.queries)
    if wiring.autopilot_enabled:
        register_backlog_promotion(wiring.pgq, control)
    register_daily_scan(wiring.pgq, control)


def _executor(wiring: WorkerMaintenance) -> MaintenanceExecutor:
    async def promote() -> int | None:
        if not wiring.autopilot_enabled:
            return None
        return await run_backlog_promotion(wiring.bridge)

    return MaintenanceExecutor(
        MaintenanceDependencies(
            dispatcher=wiring.dispatcher,
            lock=PostgresMaintenanceLock(wiring.engine),
            promotion=promote,
            recovery=lambda: run_daily_scan(wiring.scan, wiring.alert),
            coordination=PgQueuerMaintenanceGateway(wiring.queries),
        )
    )


__all__ = ["WorkerMaintenance", "maintenance_entrypoint", "register_maintenance"]
