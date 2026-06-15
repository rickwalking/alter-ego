"""SQLAlchemy model for the transactional outbox (AE-0130).

The outbox is the **single durable publish path** for workflow/release domain
events. ``WorkflowEventService.emit`` writes one row here in the **same
transaction** as the state change (transactional-outbox pattern), so an event is
durably recorded if — and only if — its business write committed. A relay
(``OutboxRelay``) is the **sole** Redis publisher: it selects unpublished rows,
publishes the stored ``payload`` to the existing stream, and marks them
published. ``event_id`` is stable, so re-processing is idempotent / at-least-once
(consumers dedupe).

The stored ``payload`` is the byte-identical ``stream_event`` dict the legacy
after-commit publisher emitted, so consumers observe no change. The event
``timestamp`` is stored verbatim as ``event_timestamp`` (the exact ISO string the
legacy path produced) so the relay reproduces it byte-identically across dialects.
"""

import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON

from rag_backend.infrastructure.database.config import Base


class EventOutboxModel(Base):
    """Durable outbox row for one workflow/release domain event."""

    __tablename__ = "event_outbox"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(36), nullable=False, unique=True)
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    aggregate_type = Column(String(50), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False, default=dict)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    # The exact ISO-8601 timestamp string the legacy after-commit publisher put in
    # the stream_event ``timestamp`` field (``datetime.now(UTC).isoformat()``,
    # tz-aware with a ``+00:00`` offset). Stored verbatim at emit time so the relay
    # republishes a byte-identical payload regardless of DB dialect (SQLite strips
    # tzinfo from DateTime round-trips; this string is immune to that).
    event_timestamp = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, server_default="0", default=0)

    __table_args__ = (
        Index("idx_outbox_unpublished", "published_at"),
        Index("idx_outbox_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_outbox_created_at", "created_at"),
    )


__all__ = ["EventOutboxModel"]
