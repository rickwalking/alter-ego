"""Background workers for scheduled publishing and deadline reminders.

``AutoRejectorFactory`` builds the auto-rejector from the worker's own event service so
the transactional outbox shares one publish path; the concrete builder is injected from
the composition root, keeping infrastructure out of the worker layer.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

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
from rag_backend.domain.protocols.blog_generation import BlogGenerationReaper
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

AutoRejectorFactory = Callable[[WorkflowEventService], StuckWorkflowAutoRejector]


class InstagramPublishTick(Protocol):
    """One Instagram publish attempt per worker tick."""

    async def tick(self, db: AsyncSession) -> int:
        """Publish or resume one due run. Returns 1 when a run was touched."""
        ...


class AutopilotRunnerTick(Protocol):
    """One in-process autopilot step per worker tick."""

    async def tick(self, db: AsyncSession) -> int:
        """Advance at most one run. Returns 1 when a run was touched."""
        ...


class TelegramNotifyTick(Protocol):
    """Deliver pending owner notices on the worker tick."""

    async def tick(self, db: AsyncSession) -> int:
        """Send due Telegram notices. Returns how many were delivered."""
        ...


class _DbStep(Protocol):
    """Any autopilot worker step: one call per tick on the tick's session."""

    async def tick(self, db: AsyncSession) -> int:
        """Do the step. Returns how many items it touched."""
        ...


_LOG_STEP_FAILED = "autopilot_worker_step_failed"


class CredentialRefreshTick(Protocol):
    """Daily Instagram token refresh."""

    async def tick(self, db: AsyncSession) -> int:
        """Refresh when due. Returns 1 when a new token was stored."""
        ...


@dataclass(frozen=True)
class WorkflowWorkerServices:
    """Composition-root-injected collaborators for the worker tick.

    Bundled so the worker keeps a 3-argument signature while gaining the
    stale-run reaper; both concrete implementations live in infrastructure
    and are built by the composition root (``bootstrap/app_factory``).

    ``blog_generation_reaper`` fails blog generation runs killed by a restart (stale
    heartbeat).
    """

    auto_rejector_factory: AutoRejectorFactory
    stale_run_reaper: CarouselStaleRunReaper | None = None
    drift_reconciler: CarouselDriftReconciler | None = None
    republish_sweeper: CarouselRepublishSweeper | None = None
    instagram_publish: InstagramPublishTick | None = None
    autopilot_runner: AutopilotRunnerTick | None = None
    telegram_notify: TelegramNotifyTick | None = None
    credential_refresh: CredentialRefreshTick | None = None
    blog_generation_reaper: BlogGenerationReaper | None = None


@dataclass(frozen=True)
class _TickCollaborators:
    """Resolved per-loop collaborators for one tick body."""

    notifications: NotificationService
    alerts: WorkflowFailureAlertService
    auto_rejector: StuckWorkflowAutoRejector
    stale_run_reaper: CarouselStaleRunReaper | None
    drift_reconciler: CarouselDriftReconciler | None
    republish_sweeper: CarouselRepublishSweeper | None
    instagram_publish: InstagramPublishTick | None = None
    autopilot_runner: AutopilotRunnerTick | None = None
    telegram_notify: TelegramNotifyTick | None = None
    credential_refresh: CredentialRefreshTick | None = None
    blog_generation_reaper: BlogGenerationReaper | None = None


async def _run_tick(
    settings: Settings,
    db: AsyncSession,
    services: _TickCollaborators,
) -> dict[str, int]:
    """One DB-session tick body.

    Pinned ordering: the stale-run reaper runs FIRST; the
    drift reconciler must run AFTER it, only over rows the
    reaper did not touch this tick, stamping the row's CURRENT epoch so the
    epoch fence never rejects its convergence writes.

    QA r1: the core steps commit before the autopilot steps run, and
    each autopilot step commits or rolls back on its own, so an autopilot
    failure never rolls back the reaper, the auto-reject, or a notice.
    """
    counters = await _core_steps(settings, db, services)
    await db.commit()
    counters.update(await _autopilot_steps(settings, db, services))
    return counters


async def _core_steps(
    settings: Settings,
    db: AsyncSession,
    services: _TickCollaborators,
) -> dict[str, int]:
    """Order matters. The drift reconciler runs after the stale-run reaper: its writes
    stamp the row's current ``run_epoch``, so the fence accepts them and a
    just-reaped row (epoch bumped) is converged on a later tick. The republish
    sweeper runs after the reconciler, so a marked-but-abandoned post-completion edit
    is rebuilt into a fresh PDF even if the client never triggered the republish.
    Interrupted blog runs are reaped alongside the carousel runs.
    """
    reaped = 0
    if services.stale_run_reaper is not None:
        reaped = await services.stale_run_reaper.tick(db)
    converged = 0
    if services.drift_reconciler is not None:
        converged = await services.drift_reconciler.reconcile(db)
    republished = 0
    if services.republish_sweeper is not None:
        republished = await services.republish_sweeper.sweep(db)
    blog_reaped = 0
    if services.blog_generation_reaper is not None:
        blog_reaped = await services.blog_generation_reaper.tick(db)
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
        "blog_reaped": blog_reaped,
        "reminders": reminders,
        "alerts": alerts,
        "auto_rejected": auto_rejected,
    }


async def _autopilot_steps(
    settings: Settings,
    db: AsyncSession,
    services: _TickCollaborators,
) -> dict[str, int]:
    """Credential refresh, publish, runner, then Telegram; each isolated."""
    runner = services.autopilot_runner if settings.autopilot_enabled else None
    steps: tuple[tuple[str, _DbStep | None], ...] = (
        ("credential_refresh", services.credential_refresh),
        ("instagram_runs", services.instagram_publish),
        ("autopilot_runs", runner),
        ("telegram_notices", services.telegram_notify),
    )
    return {name: await _isolated(name, step, db) for name, step in steps}


async def _isolated(name: str, step: _DbStep | None, db: AsyncSession) -> int:
    """Run one autopilot step in its own commit; a failure is rolled back alone."""
    if step is None:
        return 0
    try:
        count = await step.tick(db)
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(_LOG_STEP_FAILED, step=name, exc_info=True)
        return 0
    return count


async def run_workflow_workers(
    settings: Settings,
    stop_event: asyncio.Event,
    services: WorkflowWorkerServices,
) -> None:
    """Run periodic scheduled publish, reminder, reaper, and auto-reject workers.

    ``exc_info`` is bound explicitly so ``format_exc_info`` renders the traceback; a
    bare ``BoundLogger.exception()`` emitted no exception field in production.
    """
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
        instagram_publish=services.instagram_publish,
        autopilot_runner=services.autopilot_runner,
        telegram_notify=services.telegram_notify,
        credential_refresh=services.credential_refresh,
        blog_generation_reaper=services.blog_generation_reaper,
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
            logger.exception("workflow_workers_error", exc_info=True)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue
    logger.info("workflow_workers_stopped")


__all__ = ["AutoRejectorFactory", "WorkflowWorkerServices", "run_workflow_workers"]
