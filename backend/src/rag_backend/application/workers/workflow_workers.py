"""Background workers for scheduled publishing and deadline reminders."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.scheduled_publish_service import (
    ScheduledPublishService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.application.services.workflow_failure_alert_service import (
    WorkflowFailureAlertService,
)
from rag_backend.domain.protocols.carousel_run import (
    CarouselDriftReconciler,
    CarouselRepublishSweeper,
    CarouselStaleRunReaper,
)
from rag_backend.domain.protocols.workflow_timeout import StuckWorkflowAutoRejector
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.events.factory import get_event_publisher

logger = structlog.get_logger()

# Builds the auto-rejector from the worker's own event service so the
# transactional outbox shares one publish path (AE-0210). The concrete builder
# is injected from the composition root, keeping infrastructure out of the
# worker/application layer.
AutoRejectorFactory = Callable[[WorkflowEventService], StuckWorkflowAutoRejector]


@dataclass(frozen=True)
class WorkflowWorkerServices:
    """Composition-root-injected collaborators for the worker tick (AE-0315).

    Bundled so the worker keeps a 3-argument signature while gaining the
    stale-run reaper; both concrete implementations live in infrastructure
    and are built by the composition root (``bootstrap/app_factory``).
    """

    auto_rejector_factory: AutoRejectorFactory
    stale_run_reaper: CarouselStaleRunReaper | None = None
    drift_reconciler: CarouselDriftReconciler | None = None
    republish_sweeper: CarouselRepublishSweeper | None = None


@dataclass(frozen=True)
class _TickCollaborators:
    """Resolved per-loop collaborators for one tick body."""

    notifications: NotificationService
    alerts: WorkflowFailureAlertService
    auto_rejector: StuckWorkflowAutoRejector
    stale_run_reaper: CarouselStaleRunReaper | None
    drift_reconciler: CarouselDriftReconciler | None
    republish_sweeper: CarouselRepublishSweeper | None


async def _run_tick(
    settings: Settings,
    db: AsyncSession,
    services: _TickCollaborators,
) -> dict[str, int]:
    """One DB-session tick body.

    AE-0315 pinned ordering: the stale-run reaper runs FIRST; the AE-0311
    drift reconciler (when it lands) must run AFTER it, only over rows the
    reaper did not touch this tick, stamping the row's CURRENT epoch so the
    epoch fence never rejects its convergence writes.
    """
    reaped = 0
    if services.stale_run_reaper is not None:
        reaped = await services.stale_run_reaper.tick(db)
    # AE-0311: the drift reconciler runs AFTER the reaper — its convergence
    # writes stamp the row's CURRENT run_epoch, so the fence accepts them and a
    # just-reaped row (epoch bumped) is converged idempotently on a later tick.
    converged = 0
    if services.drift_reconciler is not None:
        converged = await services.drift_reconciler.reconcile(db)
    # AE-0314: the republish sweeper runs AFTER the drift reconciler — it
    # guarantees a marked-but-abandoned post-completion edit is rebuilt into a
    # fresh PDF even if the client never triggered the republish.
    republished = 0
    if services.republish_sweeper is not None:
        republished = await services.republish_sweeper.sweep(db)
    reminders = await services.notifications.send_deadline_reminders(db)
    alerts = 0
    if settings.workflow_alerts_enabled:
        alerts = await services.alerts.check_and_alert(db)
    auto_rejected = 0
    if settings.workflow_auto_reject_enabled:
        auto_rejected = await services.auto_rejector.auto_reject_stuck(
            db, settings.workflow_stuck_timeout_hours
        )
    return {
        "reaped": reaped,
        "converged": converged,
        "republished": republished,
        "reminders": reminders,
        "alerts": alerts,
        "auto_rejected": auto_rejected,
    }


async def run_workflow_workers(
    settings: Settings,
    stop_event: asyncio.Event,
    services: WorkflowWorkerServices,
) -> None:
    """Run periodic scheduled publish, reminder, reaper, and auto-reject workers."""
    session_factory = get_session_maker()
    publisher = get_event_publisher(settings.redis_url or None)
    event_service = WorkflowEventService(publisher)
    notification_service = NotificationService()
    scheduler = ScheduledPublishService(
        session_factory, event_service, notification_service
    )
    collaborators = _TickCollaborators(
        notifications=notification_service,
        alerts=WorkflowFailureAlertService(),
        auto_rejector=services.auto_rejector_factory(event_service),
        stale_run_reaper=services.stale_run_reaper,
        drift_reconciler=services.drift_reconciler,
        republish_sweeper=services.republish_sweeper,
    )
    interval = settings.workflow_worker_interval_seconds

    logger.info("workflow_workers_started", interval_seconds=interval)
    while not stop_event.is_set():
        try:
            published = await scheduler.process_due_posts()
            async with session_factory() as db:
                counters = await _run_tick(settings, db, collaborators)
                await db.commit()
            if published or any(counters.values()):
                logger.info(
                    "workflow_workers_tick",
                    published=published,
                    **counters,
                )
        except Exception:
            # AE-0212: bind exc_info explicitly so format_exc_info renders the
            # traceback. The bare BoundLogger.exception() call emitted no
            # exception field in production.
            logger.exception("workflow_workers_error", exc_info=True)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue
    logger.info("workflow_workers_stopped")


__all__ = ["AutoRejectorFactory", "WorkflowWorkerServices", "run_workflow_workers"]
