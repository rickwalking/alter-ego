"""SQLAlchemy model for workflow audit log (WF-004 event sourcing).

Also re-exports the AE-0130 outbox dispatch helpers (``build_event_records`` /
``relay_after_commit`` / ``EventRecord``). The application
``WorkflowEventService`` imports them via this module path — already grandfathered
in ``.importlinter`` (``application-no-infrastructure``) — so the transactional
outbox introduces no new application->infrastructure import edge.
"""

import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON

from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.events.outbox_dispatch import (
    EventRecord,
    build_event_records,
    relay_after_commit,
)


class WorkflowAuditLogModel(Base):
    """Immutable audit log entry for workflow domain events."""

    __tablename__ = "workflow_audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(36), nullable=False, unique=True)
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    aggregate_type = Column(String(50), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False, default=dict)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_audit_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_created_at", "created_at"),
    )


__all__ = [
    "EventRecord",
    "WorkflowAuditLogModel",
    "build_event_records",
    "relay_after_commit",
]
