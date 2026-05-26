"""Background workers for scheduled publishing and deadline reminders."""

from __future__ import annotations

import asyncio

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.scheduled_publish_service import (
    ScheduledPublishService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.application.services.workflow_failure_alert_service import (
    WorkflowFailureAlertService,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


async def run_workflow_workers(settings: Settings, stop_event: asyncio.Event) -> None:
    """Run periodic scheduled publish and deadline reminder workers."""
    session_factory = get_session_maker()
    publisher = get_event_publisher(settings.redis_url or None)
    event_service = WorkflowEventService(publisher)
    notification_service = NotificationService()
    alert_service = WorkflowFailureAlertService()
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
                await db.commit()
            if published or reminders or alerts:
                logger.info(
                    "workflow_workers_tick",
                    published=published,
                    reminders=reminders,
                    alerts=alerts,
                )
        except Exception:
            logger.exception("workflow_workers_error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue
    logger.info("workflow_workers_stopped")


__all__ = ["run_workflow_workers"]
