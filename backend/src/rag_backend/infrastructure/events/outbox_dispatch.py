"""Outbox dispatch plumbing for the transactional outbox (AE-0130).

Infrastructure-side helpers the application ``WorkflowEventService`` composes so
it never imports the ORM model, the session maker, or the relay directly (those
imports stay inside infrastructure). Two responsibilities:

* :func:`build_event_records` — construct the in-transaction audit + outbox rows
  (the application ``add``\\s them to its UoW session, so they commit atomically
  with the state change).
* :func:`relay_after_commit` — run the relay (the sole Redis publisher) against a
  fresh session after the owning transaction has committed.

These are re-exported through ``workflow_audit_log`` so the application layer's
single grandfathered import path carries them (no new application→infrastructure
edge; see ``.importlinter`` ``application-no-infrastructure``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from rag_backend.domain.protocols.event_publisher import EventPublisherProtocol
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.events.outbox_relay import OutboxRelay
from rag_backend.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from rag_backend.infrastructure.database.models.workflow_audit_log import (
        WorkflowAuditLogModel,
    )

logger = get_logger()


@dataclass(frozen=True)
class EventRecord:
    """The fields shared by the audit + outbox rows for one emitted event."""

    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    version: int
    payload: dict[str, object]
    metadata: dict[str, object]
    emitted_at: datetime


def build_event_records(
    record: EventRecord,
) -> tuple[WorkflowAuditLogModel, EventOutboxModel]:
    """Build the audit + outbox ORM rows for one emitted event.

    Both rows carry the same ``event_id``; the outbox ``created_at`` is pinned to
    ``emitted_at`` so the relay reproduces the byte-identical ``stream_event``
    timestamp the legacy after-commit publisher emitted.
    """
    from rag_backend.infrastructure.database.models.workflow_audit_log import (
        WorkflowAuditLogModel,
    )

    audit = WorkflowAuditLogModel(
        event_id=record.event_id,
        event_type=record.event_type,
        aggregate_id=record.aggregate_id,
        aggregate_type=record.aggregate_type,
        version=record.version,
        payload=record.payload,
        metadata_json=record.metadata,
    )
    outbox = EventOutboxModel(
        event_id=record.event_id,
        event_type=record.event_type,
        aggregate_id=record.aggregate_id,
        aggregate_type=record.aggregate_type,
        version=record.version,
        payload=record.payload,
        metadata_json=record.metadata,
        created_at=record.emitted_at,
        attempts=0,
    )
    return audit, outbox


async def relay_after_commit(publisher: EventPublisherProtocol) -> None:
    """Run one relay pass against a fresh session (the sole Redis publisher).

    Failures are logged, never raised — unpublished rows are retried on the next
    relay pass (at-least-once).
    """
    from rag_backend.infrastructure.database.config import get_session_maker

    session_maker = get_session_maker()
    try:
        async with session_maker() as session:
            await OutboxRelay(publisher).run_once(session)
            await session.commit()
    except Exception as exc:  # transport/session failure must not propagate
        logger.warning("outbox_relay_pass_failed", error=str(exc))


__all__ = ["EventRecord", "build_event_records", "relay_after_commit"]
