"""Entry of the generation worker: ``pgq run rag_backend.worker.main:create_pgqueuer``.

Builds what the web app builds for carousel work (settings, observability, DB
engine without ``create_all``, the Postgres checkpointer, the editorial engine)
but starts no HTTP server. It registers one PgQueuer entrypoint for every kind of
generation work, so ``concurrency_limit`` (``GENERATION_WORKER_CONCURRENCY``,
Pedro: 1) is global and FIFO holds across kinds, and runs the dispatcher and the
heavy periodic steps next to it. On SIGTERM PgQueuer stops dequeuing; a drive
stops at its next phase boundary and comes back at once on the next worker.

The worker refuses to start unless the checkpointer is ``postgres``: the web
reads the state the worker writes, so an in-memory or SQLite checkpointer would
split them.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Final

from pgqueuer import PgQueuer
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.errors import RetryRequested
from pgqueuer.domain.models import Job

from rag_backend.agents.harness import build_checkpointer
from rag_backend.application.services.carousel.provider_errors import (
    classify_provider_error,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    install_workflow_sse_hub,
)
from rag_backend.bootstrap.autopilot_worker_factory import (
    autopilot_engine_factory,
    autopilot_tick_config,
)
from rag_backend.bootstrap.carousel_drift_reconciler_factory import (
    build_drift_reconciler,
)
from rag_backend.bootstrap.carousel_republish_sweeper_factory import (
    build_republish_sweeper,
)
from rag_backend.bootstrap.carousel_run_reaper_factory import (
    build_run_reaper_repository,
)
from rag_backend.bootstrap.observability import init_observability
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.database.config import (
    attach_db,
    close_db,
    get_session_maker,
)
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.notifications.llm_alerts import TelegramLlmAlerts
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    VerdictKind,
)
from rag_backend.modules.generation_queue.bootstrap import (
    HandlerParts,
    compose_worker,
)
from rag_backend.modules.generation_queue.constants import (
    ENTRYPOINT,
    LOG_WORKER_STARTED,
    LOG_WORKER_STOPPED,
    WORKER_APPLICATION_NAME,
)
from rag_backend.modules.generation_queue.domain.errors import DeadLetteredError
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import run_id_of
from rag_backend.modules.generation_queue.infrastructure.progress_relay import (
    RelayingWorkflowSseHub,
    engine_notifier,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    asyncpg_connection,
)
from rag_backend.worker.periodic import PeriodicSteps, run_dispatcher, run_periodic
from rag_backend.worker.recovery import register_daily_scan
from rag_backend.worker.schedules import register_backlog_promotion

logger = get_logger()

CHECKPOINT_BACKEND_POSTGRES = "postgres"
ON_FAILURE_HOLD: Final = "hold"
SET_APPLICATION_NAME = f"SET application_name = '{WORKER_APPLICATION_NAME}'"
ERR_CHECKPOINTER = (
    "generation worker needs CAROUSEL_CHECKPOINT_BACKEND=postgres, got {backend!r}"
)


class WorkerConfigError(RuntimeError):
    """The worker cannot run with this configuration."""


def require_postgres_checkpointer(settings: Settings) -> None:
    """Refuse to start on a checkpointer the web process cannot read."""
    backend = settings.carousel_checkpoint_backend.lower()
    if backend != CHECKPOINT_BACKEND_POSTGRES:
        raise WorkerConfigError(ERR_CHECKPOINTER.format(backend=backend))


def is_provider_error(exc: BaseException) -> bool:
    """Provider outages and rate limits are transient for the queue."""
    return classify_provider_error(exc) is not None


def job_entrypoint(handler: GenerationJobHandler) -> Callable[[Job], Awaitable[None]]:
    """The PgQueuer entrypoint: turn the handler's verdict into PgQueuer signals."""

    async def run(job: Job) -> None:
        run_id = run_id_of(job.payload)
        if run_id is None:
            return
        verdict = await handler.handle(run_id)
        if verdict.kind is VerdictKind.RETRY:
            raise RetryRequested(delay=verdict.delay, reason=str(run_id))
        if verdict.kind is VerdictKind.HOLD:
            raise DeadLetteredError(str(run_id))

    return run


@asynccontextmanager
async def create_pgqueuer() -> AsyncIterator[PgQueuer]:
    """Build the worker; tear its loops, pools and engine down on exit."""
    settings = get_settings()
    init_observability(settings)
    require_postgres_checkpointer(settings)
    engine = attach_db(
        settings.database_url,
        settings.generation_worker_db_pool_size,
        settings.generation_worker_db_max_overflow,
    )
    install_workflow_sse_hub(RelayingWorkflowSseHub(engine_notifier(engine)))
    async with AsyncExitStack() as stack:
        stack.push_async_callback(close_db)
        connection = await stack.enter_async_context(asyncpg_connection(engine))
        await connection.execute(SET_APPLICATION_NAME)
        pgq = PgQueuer(AsyncpgDriver(connection))
        checkpointer = await build_checkpointer(settings, stack)
        engine_factory = autopilot_engine_factory(checkpointer)
        sessions = get_session_maker()
        bridge = AutopilotQueueBridge(
            config=autopilot_tick_config(settings, engine_factory),
            sessions=sessions,
            retryable=is_provider_error,
        )
        reaper = build_run_reaper_repository(settings, checkpointer)
        composition = compose_worker(
            HandlerParts(
                engine=engine,
                sessions=sessions,
                bridge=bridge,
                reaper=reaper,
                engine_factory=engine_factory,
                is_provider_error=is_provider_error,
                stopping=lambda: pgq.shutdown.is_set(),
                drive_autopilot=settings.autopilot_enabled,
            ),
            Queries(pgq.connection),
        )
        pgq.entrypoint(
            ENTRYPOINT,
            concurrency_limit=settings.generation_worker_concurrency,
            on_failure=ON_FAILURE_HOLD,
        )(job_entrypoint(composition.handler))
        if settings.autopilot_enabled:
            register_backlog_promotion(pgq, bridge)
        alerts = TelegramLlmAlerts(
            token=settings.telegram_alerts_bot_token.get_secret_value(),
            chat_id=settings.telegram_alerts_chat_id,
        )
        register_daily_scan(pgq, composition.scan, alerts.send)
        loops = [
            asyncio.create_task(
                run_dispatcher(
                    composition.dispatcher,
                    lambda: pgq.shutdown,
                    settings.generation_worker_alive_file,
                )
            ),
            asyncio.create_task(
                run_periodic(
                    PeriodicSteps(
                        sessions=sessions,
                        reaper=reaper,
                        drift=build_drift_reconciler(checkpointer),
                        republish=build_republish_sweeper(settings),
                        bridge=bridge,
                    ),
                    lambda: pgq.shutdown,
                    settings.workflow_worker_interval_seconds,
                )
            ),
        ]
        logger.info(
            LOG_WORKER_STARTED, concurrency=settings.generation_worker_concurrency
        )
        try:
            yield pgq
        finally:
            pgq.shutdown.set()
            await asyncio.gather(*loops, return_exceptions=True)
            logger.info(LOG_WORKER_STOPPED)


__all__ = [
    "WorkerConfigError",
    "create_pgqueuer",
    "is_provider_error",
    "job_entrypoint",
    "require_postgres_checkpointer",
]
