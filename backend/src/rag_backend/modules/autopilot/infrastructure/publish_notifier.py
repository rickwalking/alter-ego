"""Persist a publish notice on the transactional outbox.

AE-0355 delivers ``content.autopilot.*`` to Telegram. This adapter only
records the notice in the same session as the state change.
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
    CALLBACK_RETRY_PREFIX,
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_VERSION,
    METADATA_MODULE,
    MODULE_NAME,
    PAYLOAD_ERROR_CODE,
    PAYLOAD_OFFER_RETRY,
    PAYLOAD_OUTCOME,
    PAYLOAD_PERMALINK,
    PAYLOAD_RETRY_CALLBACK,
)
from rag_backend.modules.autopilot.domain.publish import PublishNotice


class OutboxPublishNotifier:
    """Writes one outbox row per notice. Does not call Telegram."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def notify(self, notice: PublishNotice) -> None:
        """Stage the notice. The caller commits."""
        audit, outbox = build_event_records(_record(notice))
        self._session.add(audit)
        self._session.add(outbox)
        await self._session.flush()


def _record(notice: PublishNotice) -> EventRecord:
    callback: str | None = None
    if notice.offer_retry:
        callback = f"{CALLBACK_RETRY_PREFIX}{notice.run_id}"
    return EventRecord(
        event_id=str(uuid4()),
        event_type=EVENT_TYPE_PUBLISH_NOTICE,
        aggregate_id=str(notice.run_id),
        aggregate_type=AGGREGATE_TYPE_AUTOPILOT_RUN,
        version=EVENT_VERSION,
        payload={
            PAYLOAD_OUTCOME: notice.outcome,
            PAYLOAD_PERMALINK: notice.permalink,
            PAYLOAD_ERROR_CODE: notice.error_code,
            PAYLOAD_OFFER_RETRY: notice.offer_retry,
            PAYLOAD_RETRY_CALLBACK: callback,
        },
        metadata={METADATA_MODULE: MODULE_NAME},
        emitted_at=datetime.now(UTC),
    )
