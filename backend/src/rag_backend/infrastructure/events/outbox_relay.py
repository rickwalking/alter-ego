"""Transactional-outbox relay — the sole durable Redis publisher (AE-0130).

The relay reads unpublished ``event_outbox`` rows (``published_at IS NULL``),
publishes each stored ``stream_event`` payload to the existing Redis stream, and
marks the row published (bumping ``attempts``). It is the **single** Redis
publisher for workflow/release events: ``WorkflowEventService.emit`` only writes
the outbox row in-transaction, and this relay drains it after commit.

Delivery is **at-least-once + idempotent**:

* Only ``published_at IS NULL`` rows are selected, so re-running the relay never
  re-publishes an already-marked row (idempotent at the relay).
* If the process crashes between the Redis publish and the ``published_at`` mark,
  the row is re-selected on the next run and re-published — at-least-once. The
  ``event_id`` is stable, so consumers dedupe and re-processing yields the same
  result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
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
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_DEFAULT_BATCH_SIZE = 100


def outbox_stream_event(row: EventOutboxModel) -> dict[str, object]:
    """Rebuild the byte-identical ``stream_event`` payload from an outbox row.

    Mirrors the dict ``WorkflowEventService.emit`` stored, so the relay publishes
    exactly what the legacy after-commit path published.
    """
    timestamp = row.created_at.isoformat() if row.created_at is not None else ""
    return {
        EVENT_FIELD_EVENT_ID: row.event_id,
        EVENT_FIELD_EVENT_TYPE: row.event_type,
        EVENT_FIELD_AGGREGATE_ID: row.aggregate_id,
        EVENT_FIELD_AGGREGATE_TYPE: row.aggregate_type,
        EVENT_FIELD_TIMESTAMP: timestamp,
        EVENT_FIELD_VERSION: row.version,
        EVENT_FIELD_PAYLOAD: row.payload,
        EVENT_FIELD_METADATA: row.metadata_json,
    }


@dataclass(frozen=True)
class OutboxRelayResult:
    """Outcome of one relay pass."""

    published: int
    failed: int


class OutboxRelay:
    """Publishes unpublished outbox rows to Redis, idempotently (at-least-once)."""

    def __init__(self, publisher: EventPublisherProtocol) -> None:
        self._publisher = publisher

    async def run_once(
        self, db: AsyncSession, *, batch_size: int = _DEFAULT_BATCH_SIZE
    ) -> OutboxRelayResult:
        """Publish one batch of unpublished rows; mark each published row.

        Each row is published before its ``published_at`` is stamped, so a crash
        in between re-delivers (at-least-once). Transport failures leave the row
        unpublished for the next pass and are counted, never raised.
        """
        rows = await self._unpublished_rows(db, batch_size)
        published = 0
        failed = 0
        for row in rows:
            if await self._publish_row(row):
                published += 1
            else:
                failed += 1
        await db.flush()
        return OutboxRelayResult(published=published, failed=failed)

    @staticmethod
    async def _unpublished_rows(
        db: AsyncSession, batch_size: int
    ) -> list[EventOutboxModel]:
        result = await db.execute(
            select(EventOutboxModel)
            .where(EventOutboxModel.published_at.is_(None))
            .order_by(EventOutboxModel.created_at)
            .limit(batch_size)
        )
        return list(result.scalars().all())

    async def _publish_row(self, row: EventOutboxModel) -> bool:
        """Publish one row to Redis and mark it published; True on success."""
        try:
            await self._publisher.publish(
                STREAM_CONTENT_EVENTS, outbox_stream_event(row)
            )
        except Exception as exc:  # transport failure: retry on the next pass
            row.attempts = (row.attempts or 0) + 1
            logger.warning(
                "outbox_relay_publish_failed",
                event_id=row.event_id,
                attempts=row.attempts,
                error=str(exc),
            )
            return False
        row.attempts = (row.attempts or 0) + 1
        row.published_at = datetime.now(UTC)
        return True


__all__ = ["OutboxRelay", "OutboxRelayResult", "outbox_stream_event"]
