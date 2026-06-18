"""Background workers for scheduled publishing and deadline reminders."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.scheduled_publish_service import (
    ScheduledPublishService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.application.services.workflow_failure_alert_service import (
    WorkflowFailureAlertService,
)
from rag_backend.domain.protocols.workflow_timeout import StuckWorkflowAutoRejector
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

# Builds the auto-rejector from the worker's own event service so the
# transactional outbox shares one publish path (AE-0210). The concrete builder
# is injected from the composition root, keeping infrastructure out of the
# worker/application layer.
AutoRejectorFactory = Callable[[WorkflowEventService], StuckWorkflowAutoRejector]


async def run_workflow_workers(
    settings: Settings,
    stop_event: asyncio.Event,
    auto_rejector_factory: AutoRejectorFactory,
) -> None:
    """Run periodic scheduled publish, deadline reminder, and auto-reject workers."""
    session_factory = get_session_maker()
    publisher = get_event_publisher(settings.redis_url or None)
    event_service = WorkflowEventService(publisher)
    notification_service = NotificationService()
    alert_service = WorkflowFailureAlertService()
    timeout_service = auto_rejector_factory(event_service)
    scheduler = ScheduledPublishService(
        session_factory, event_service, notification_service
    )
    interval = settings.workflow_worker_interval_seconds

    logger.info("workflow_workers_started", interval_seconds=interval)
    while not stop_event.is_set():
        try:
            published = await scheduler.process_due_posts()
            async with session_factory() as db:
                reminders = await notification_service.send_deadline_reminders(db)
                alerts = 0
                if settings.workflow_alerts_enabled:
                    alerts = await alert_service.check_and_alert(db)
                auto_rejected = 0
                if settings.workflow_auto_reject_enabled:
                    auto_rejected = await timeout_service.auto_reject_stuck(
                        db, settings.workflow_stuck_timeout_hours
                    )
                await db.commit()
            if published or reminders or alerts or auto_rejected:
                logger.info(
                    "workflow_workers_tick",
                    published=published,
                    reminders=reminders,
                    alerts=alerts,
                    auto_rejected=auto_rejected,
                )
        except Exception:
            logger.exception("workflow_workers_error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue
    logger.info("workflow_workers_stopped")


__all__ = ["AutoRejectorFactory", "run_workflow_workers"]
