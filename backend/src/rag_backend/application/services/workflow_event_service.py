"""Workflow event publishing via the transactional outbox (WF-001, WF-004).

``emit`` writes the audit row **and** the outbox row in the SAME transaction as
the state change (transactional-outbox pattern, AE-0130), then queues the event
for the post-commit relay. A rollback discards both rows and the queue, keeping
the stream consistent with PostgreSQL (AE-0074).

The outbox is the **single durable publish path**: ``emit`` never publishes to
Redis directly. After the owning transaction commits, the ``after_commit``
listener runs the relay (the **sole** Redis publisher), which selects unpublished
rows, publishes the byte-identical ``stream_event`` payload, and marks them
published. Delivery is at-least-once + idempotent (stable ``event_id``); the
``published_at`` mark prevents double delivery across relay passes.

ORM access stays in infrastructure: ``emit`` builds the rows through
``build_event_records`` and the relay runs through ``relay_after_commit``, both
re-exported from ``workflow_audit_log`` (the grandfathered import path).
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

from rag_backend.domain.constants.workflow_events import SESSION_INFO_PENDING_EVENTS
from rag_backend.domain.protocols.event_publisher import EventPublisherProtocol
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    EventRecord,
    WorkflowAuditLogModel,
    build_event_records,
    relay_after_commit,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_PendingRelay = EventPublisherProtocol

_inflight_publishes: set[asyncio.Task[None]] = set()


@dataclass(frozen=True)
class _AggregateQuery:
    """Query filters for listing audit events for an aggregate."""

    aggregate_type: str
    aggregate_id: str
    limit: int = 100


class WorkflowEventService:
    """Persists audit + outbox entries and relays events after commit."""

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
        """Store the audit + outbox rows in-txn; queue the post-commit relay."""
        event_id = str(uuid.uuid4())
        record = EventRecord(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            version=version,
            payload=payload,
            metadata=metadata or {},
            emitted_at=datetime.now(UTC),
        )
        audit, outbox = build_event_records(record)
        db.add(audit)
        db.add(outbox)
        await db.flush()
        _queue_pending(db.sync_session, self._publisher)
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


def _queue_pending(session: Session, publisher: _PendingRelay) -> None:
    """Record that this committed session has outbox rows awaiting relay."""
    queued = cast(
        "list[_PendingRelay]",
        session.info.setdefault(SESSION_INFO_PENDING_EVENTS, []),
    )
    queued.append(publisher)


async def _relay_pending(publishers: list[_PendingRelay]) -> None:
    """Drain the outbox via the relay (the sole Redis publisher).

    Runs one relay pass per distinct publisher; failures are logged inside the
    relay, never raised — unpublished rows are retried on the next pass.
    """
    for publisher in _unique_publishers(publishers):
        await relay_after_commit(publisher)


def _unique_publishers(publishers: list[_PendingRelay]) -> list[_PendingRelay]:
    """De-duplicate publishers by identity, preserving order."""
    seen: list[_PendingRelay] = []
    for publisher in publishers:
        if all(publisher is not existing for existing in seen):
            seen.append(publisher)
    return seen


def _schedule_relay(publishers: list[_PendingRelay]) -> None:
    """Run the post-commit relay as a tracked background task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError as exc:
        logger.warning(
            "workflow_event_relay_no_loop",
            dropped_publishers=len(publishers),
            error=str(exc),
        )
        return
    task = loop.create_task(_relay_pending(publishers))
    _inflight_publishes.add(task)
    task.add_done_callback(_inflight_publishes.discard)


@event.listens_for(Session, "after_commit")
def _on_session_commit(session: Session) -> None:
    """Relay outbox rows once their transaction commits (single publish path)."""
    pending = cast(
        "list[_PendingRelay] | None",
        session.info.pop(SESSION_INFO_PENDING_EVENTS, None),
    )
    if pending:
        _schedule_relay(list(pending))


@event.listens_for(Session, "after_rollback")
def _on_session_rollback(session: Session) -> None:
    """Discard queued relays when their transaction rolls back."""
    session.info.pop(SESSION_INFO_PENDING_EVENTS, None)


async def drain_pending_publishes() -> None:
    """Await all in-flight post-commit relays (tests and shutdown)."""
    while _inflight_publishes:
        await asyncio.gather(*list(_inflight_publishes), return_exceptions=True)


__all__ = ["WorkflowEventService", "drain_pending_publishes"]
