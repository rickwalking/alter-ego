"""Stage ``content.autopilot.ready_for_owner`` on the transactional outbox.

Delivers the event to Telegram. This adapter only records it in
the same session as the state change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.events.outbox_dispatch import (
    EventRecord,
    build_event_records,
)
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
    EVENT_TYPE_READY_FOR_OWNER,
    EVENT_VERSION,
    METADATA_MODULE,
    MODULE_NAME,
    PAYLOAD_PROJECT_ID,
)
from rag_backend.modules.autopilot.domain.gate import OwnerReadyNotice
from rag_backend.modules.autopilot.notify_constants import (
    PAYLOAD_PERSONA_SCORE,
    PAYLOAD_REVISION,
    PAYLOAD_SOURCES_COUNT,
)


class OutboxReadyNotifier:
    """Writes one ready-for-owner row. Does not call Telegram."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def notify_ready(self, notice: OwnerReadyNotice) -> None:
        """Stage the event. The caller commits."""
        audit, outbox = build_event_records(_record(notice))
        self._session.add(audit)
        self._session.add(outbox)
        await self._session.flush()


def _record(notice: OwnerReadyNotice) -> EventRecord:
    return EventRecord(
        event_id=str(uuid4()),
        event_type=EVENT_TYPE_READY_FOR_OWNER,
        aggregate_id=str(notice.run_id),
        aggregate_type=AGGREGATE_TYPE_AUTOPILOT_RUN,
        version=EVENT_VERSION,
        payload={
            PAYLOAD_PROJECT_ID: notice.project_id,
            PAYLOAD_REVISION: notice.revision,
            PAYLOAD_PERSONA_SCORE: notice.persona_score,
            PAYLOAD_SOURCES_COUNT: notice.sources_count,
        },
        metadata={METADATA_MODULE: MODULE_NAME},
        emitted_at=datetime.now(UTC),
    )
