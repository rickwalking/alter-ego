"""Manual recovery audit through the existing workflow audit/outbox service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.modules.generation_queue.constants import (
    AGGREGATE_CAROUSEL,
    AGGREGATE_GENERATION_RUN,
    AUDIT_CAROUSEL_REPROCESS,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import AuditCommand


class SqlManualRecoveryAudit:
    """Write the allowlisted event on the recovery session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        settings = get_settings()
        self._events = WorkflowEventService(
            get_event_publisher(settings.redis_url or None)
        )

    async def record(self, command: AuditCommand) -> None:
        """Persist actor/project/run/kind/version and no content or error text."""
        payload: dict[str, object] = {
            "actor_id": command.actor_id,
            "project_id": command.project_id,
            "run_id": str(command.run_id),
            "stuck_kind": command.stuck_kind.value,
            "lock_version": command.lock_version,
        }
        aggregate_id = command.project_id or str(command.run_id)
        aggregate_type = (
            AGGREGATE_CAROUSEL if command.project_id else AGGREGATE_GENERATION_RUN
        )
        await self._events.emit(
            self._session,
            event_type=AUDIT_CAROUSEL_REPROCESS,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload,
            metadata={},
            version=command.lock_version or 1,
        )


__all__ = ["SqlManualRecoveryAudit"]
