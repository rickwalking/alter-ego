"""Workflow event publishing with PostgreSQL audit log (WF-001, WF-004)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.workflow_events import (
    EVENT_FIELD_AGGREGATE_ID,
    EVENT_FIELD_AGGREGATE_TYPE,
    EVENT_FIELD_EVENT_ID,
    EVENT_FIELD_EVENT_TYPE,
    EVENT_FIELD_METADATA,
    EVENT_FIELD_PAYLOAD,
    EVENT_FIELD_TIMESTAMP,
    EVENT_FIELD_VERSION,
    STREAM_CONTENT_EVENTS,
)
from rag_backend.domain.protocols.event_publisher import EventPublisherProtocol
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)


class WorkflowEventService:
    """Publishes events to Redis Streams and persists audit log entries."""

    def __init__(self, publisher: EventPublisherProtocol) -> None:
        self._publisher = publisher

    async def emit(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, object],
        metadata: dict[str, object] | None = None,
        version: int = 1,
    ) -> str:
        """Publish event and store immutable audit record."""
        event_id = str(uuid.uuid4())
        event: dict[str, object] = {
            EVENT_FIELD_EVENT_ID: event_id,
            EVENT_FIELD_EVENT_TYPE: event_type,
            EVENT_FIELD_AGGREGATE_ID: aggregate_id,
            EVENT_FIELD_AGGREGATE_TYPE: aggregate_type,
            EVENT_FIELD_TIMESTAMP: datetime.now(UTC).isoformat(),
            EVENT_FIELD_VERSION: version,
            EVENT_FIELD_PAYLOAD: payload,
            EVENT_FIELD_METADATA: metadata or {},
        }
        stream_entry_id = await self._publisher.publish(STREAM_CONTENT_EVENTS, event)
        audit = WorkflowAuditLogModel(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            version=version,
            payload=payload,
            metadata_json=metadata or {},
            stream_entry_id=stream_entry_id,
        )
        db.add(audit)
        await db.flush()
        return event_id

    async def list_for_aggregate(
        self,
        db: AsyncSession,
        *,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 100,
    ) -> list[WorkflowAuditLogModel]:
        """Query audit log for a specific aggregate."""
        from sqlalchemy import select

        result = await db.execute(
            select(WorkflowAuditLogModel)
            .where(
                WorkflowAuditLogModel.aggregate_type == aggregate_type,
                WorkflowAuditLogModel.aggregate_id == aggregate_id,
            )
            .order_by(WorkflowAuditLogModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


__all__ = ["WorkflowEventService"]
