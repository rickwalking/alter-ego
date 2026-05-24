"""SQLAlchemy model for workflow audit log (WF-004 event sourcing)."""

import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON

from rag_backend.infrastructure.database.config import Base


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
    stream_entry_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_audit_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_created_at", "created_at"),
    )


__all__ = ["WorkflowAuditLogModel"]
