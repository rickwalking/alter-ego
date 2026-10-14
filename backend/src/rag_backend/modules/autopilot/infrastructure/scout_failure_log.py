"""Delivered scout failures, stored as outbox rows (QA r1 S-W3).

The outbox table already exists, so no migration is needed. The aggregate
type is not ``autopilot_run``, so the Telegram dispatcher never re-sends
these rows; the relay only republishes them to Redis.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.events.outbox_dispatch import (
    EventRecord,
    build_event_records,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_VERSION,
    METADATA_MODULE,
    MODULE_NAME,
)
from rag_backend.modules.autopilot.domain.scout_ports import ScoutFailureEntry
from rag_backend.modules.autopilot.infrastructure.advisory_lock import (
    advisory_xact_lock,
)
from rag_backend.modules.autopilot.scout_constants import (
    AGGREGATE_TYPE_AUTOPILOT_SCOUT,
    EVENT_TYPE_SCOUT_FAILED,
    PAYLOAD_SCOUT_REASON,
    SCOUT_FAILURE_LOCK_KEY,
)


class OutboxScoutFailureLog:
    """``ScoutFailureLog`` over the transactional outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock(self) -> None:
        """Serialize the cap check with concurrent requests until the commit."""
        await advisory_xact_lock(self._session, SCOUT_FAILURE_LOCK_KEY)

    async def reasons_since(self, since: datetime) -> tuple[str, ...]:
        """Reasons of scout-failed rows created at or after ``since``."""
        result = await self._session.execute(
            select(EventOutboxModel.payload)
            .where(
                EventOutboxModel.aggregate_type == AGGREGATE_TYPE_AUTOPILOT_SCOUT,
                EventOutboxModel.event_type == EVENT_TYPE_SCOUT_FAILED,
                EventOutboxModel.created_at >= since,
            )
            .order_by(EventOutboxModel.created_at.asc())
        )
        payloads = [cast(object, row) for row in result.scalars().all()]
        return tuple(_reason(payload) for payload in payloads)

    async def record(self, entry: ScoutFailureEntry) -> None:
        """Stage the audit and outbox rows for one delivered failure."""
        audit, outbox = build_event_records(_record(entry))
        self._session.add(audit)
        self._session.add(outbox)
        await self._session.flush()

    async def commit(self) -> None:
        """Commit (releasing the lock) so a later request sees this failure."""
        await self._session.commit()


def _record(entry: ScoutFailureEntry) -> EventRecord:
    event_id = str(uuid4())
    return EventRecord(
        event_id=event_id,
        event_type=EVENT_TYPE_SCOUT_FAILED,
        aggregate_id=event_id,
        aggregate_type=AGGREGATE_TYPE_AUTOPILOT_SCOUT,
        version=EVENT_VERSION,
        payload={PAYLOAD_SCOUT_REASON: entry.reason},
        metadata={METADATA_MODULE: MODULE_NAME},
        emitted_at=entry.sent_at,
    )


def _reason(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    value = cast(dict[str, object], payload).get(PAYLOAD_SCOUT_REASON)
    if isinstance(value, str):
        return value
    return ""
