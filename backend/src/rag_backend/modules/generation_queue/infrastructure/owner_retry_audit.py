"""Owner Retry audit through the existing workflow audit/outbox service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.modules.generation_queue.constants import (
    AGGREGATE_CAROUSEL,
    AUDIT_CAROUSEL_RETRY,
)
from rag_backend.modules.generation_queue.domain.owner_retry_ports import (
    RetryAuditCommand,
)


class SqlOwnerRetryAudit:
    """Write the allowlisted ``carousel.retry.requested`` event on the session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        settings = get_settings()
        self._events = WorkflowEventService(
            get_event_publisher(settings.redis_url or None)
        )

    async def record(self, command: RetryAuditCommand) -> None:
        """Actor, surface, kind, phase, versions, run, reason and feedback line.

        The feedback line is the fixed system line a revise sent (empty for a
        re-drive or a reopen); no carousel content is stored.
        """
        plan, write = command.plan, command.write
        run_id = write.autopilot_run_id
        payload: dict[str, object] = {
            "actor_id": plan.command.actor_id,
            "surface": plan.command.surface.value,
            "project_id": plan.command.project_id,
            "retry_kind": plan.kind.value,
            "phase": plan.facts.carousel.phase,
            "previous_phase_status": plan.facts.carousel.phase_status,
            "lock_version": write.lock_version,
            "autopilot_run_id": str(run_id) if run_id is not None else None,
            "reason": plan.reason,
            "feedback": plan.feedback,
        }
        await self._events.emit(
            self._session,
            event_type=AUDIT_CAROUSEL_RETRY,
            aggregate_id=plan.command.project_id,
            aggregate_type=AGGREGATE_CAROUSEL,
            payload=payload,
            metadata={},
            version=write.lock_version or 1,
        )


__all__ = ["SqlOwnerRetryAudit"]
