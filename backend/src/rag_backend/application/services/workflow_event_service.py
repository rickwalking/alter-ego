"""Workflow event publishing with PostgreSQL audit log (WF-001, WF-004).

Events are queued on the session during the transaction and published to
Redis only after the owning transaction commits (AE-0074). A rollback
discards queued events, keeping the stream consistent with PostgreSQL.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from rag_backend.domain.constants.workflow_events import (
    EVENT_FIELD_AGGREGATE_ID,
    EVENT_FIELD_AGGREGATE_TYPE,
    EVENT_FIELD_EVENT_ID,
    EVENT_FIELD_EVENT_TYPE,
    EVENT_FIELD_METADATA,
    EVENT_FIELD_PAYLOAD,
    EVENT_FIELD_TIMESTAMP,
    EVENT_FIELD_VERSION,
    SESSION_INFO_PENDING_EVENTS,
    STREAM_CONTENT_EVENTS,
)
from rag_backend.domain.protocols.event_publisher import EventPublisherProtocol
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_PendingPublish = tuple[EventPublisherProtocol, dict[str, object]]

_inflight_publishes: set[asyncio.Task[None]] = set()


@dataclass(frozen=True)
class _AggregateQuery:
    """Query filters for listing audit events for an aggregate."""

    aggregate_type: str
    aggregate_id: str
    limit: int = 100


class WorkflowEventService:
    """Persists audit entries and publishes events after commit."""

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
        """Store the audit record and queue the event for post-commit publish."""
        event_id = str(uuid.uuid4())
        stream_event: dict[str, object] = {
            EVENT_FIELD_EVENT_ID: event_id,
            EVENT_FIELD_EVENT_TYPE: event_type,
            EVENT_FIELD_AGGREGATE_ID: aggregate_id,
            EVENT_FIELD_AGGREGATE_TYPE: aggregate_type,
            EVENT_FIELD_TIMESTAMP: datetime.now(UTC).isoformat(),
            EVENT_FIELD_VERSION: version,
            EVENT_FIELD_PAYLOAD: payload,
            EVENT_FIELD_METADATA: metadata or {},
        }
        audit = WorkflowAuditLogModel(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            version=version,
            payload=payload,
            metadata_json=metadata or {},
        )
        db.add(audit)
        await db.flush()
        _queue_pending(db.sync_session, (self._publisher, stream_event))
        return event_id

    @staticmethod
    async def list_for_aggregate(
        db: AsyncSession,
        query_params: _AggregateQuery,
    ) -> list[WorkflowAuditLogModel]:
        """Query audit log for a specific aggregate."""
        from sqlalchemy import select

        result = await db.execute(
            select(WorkflowAuditLogModel)
            .where(
                WorkflowAuditLogModel.aggregate_type == query_params.aggregate_type,
                WorkflowAuditLogModel.aggregate_id == query_params.aggregate_id,
            )
            .order_by(WorkflowAuditLogModel.created_at.desc())
            .limit(query_params.limit)
        )
        return list(result.scalars().all())


def _queue_pending(session: Session, pending: _PendingPublish) -> None:
    """Append a queued publish to the session's pending-event list."""
    queued = cast(
        "list[_PendingPublish]",
        session.info.setdefault(SESSION_INFO_PENDING_EVENTS, []),
    )
    queued.append(pending)


async def _publish_events(pending: list[_PendingPublish]) -> None:
    """Publish queued events; failures are logged, never raised."""
    for publisher, stream_event in pending:
        try:
            await publisher.publish(STREAM_CONTENT_EVENTS, stream_event)
        except Exception as exc:  # transport failure must not reach callers
            logger.warning(
                "workflow_event_publish_failed",
                event_id=stream_event.get(EVENT_FIELD_EVENT_ID),
                error=str(exc),
            )


def _schedule_publish(pending: list[_PendingPublish]) -> None:
    """Run the post-commit publish as a tracked background task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.exception(
            "workflow_event_publish_no_loop",
            dropped_events=len(pending),
        )
        return
    task = loop.create_task(_publish_events(pending))
    _inflight_publishes.add(task)
    task.add_done_callback(_inflight_publishes.discard)


@event.listens_for(Session, "after_commit")
def _on_session_commit(session: Session) -> None:
    """Publish events queued by emit() once their transaction commits."""
    pending = cast(
        "list[_PendingPublish] | None",
        session.info.pop(SESSION_INFO_PENDING_EVENTS, None),
    )
    if pending:
        _schedule_publish(list(pending))


@event.listens_for(Session, "after_rollback")
def _on_session_rollback(session: Session) -> None:
    """Discard queued events when their transaction rolls back."""
    session.info.pop(SESSION_INFO_PENDING_EVENTS, None)


async def drain_pending_publishes() -> None:
    """Await all in-flight post-commit publishes (tests and shutdown)."""
    while _inflight_publishes:
        await asyncio.gather(*list(_inflight_publishes), return_exceptions=True)


__all__ = ["WorkflowEventService", "drain_pending_publishes"]
