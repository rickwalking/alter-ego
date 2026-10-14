"""Outbox window and notice-ledger writes for the Telegram dispatcher."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
)
from rag_backend.modules.autopilot.domain.notice_log import dump_log
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    SaveNoticeLog,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.notify_constants import (
    NOTIFY_EVENT_TYPES,
    OUTBOX_SCAN_LIMIT,
)


class SqlAutopilotEventSource:
    """The newest ``content.autopilot.*`` rows. Delivery dedupe is the ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent(self) -> list[AutopilotOutboxEvent]:
        """Return up to the scan limit, newest first."""
        result = await self._session.execute(
            select(EventOutboxModel)
            .where(
                EventOutboxModel.aggregate_type == AGGREGATE_TYPE_AUTOPILOT_RUN,
                EventOutboxModel.event_type.in_(NOTIFY_EVENT_TYPES),
            )
            .order_by(EventOutboxModel.created_at.desc())
            .limit(OUTBOX_SCAN_LIMIT)
        )
        events = [_event(row) for row in result.scalars().all()]
        return [event for event in events if event is not None]


class SqlNoticeLogStore:
    """Updates ``telegram_message_ids`` and leaves ``updated_at`` alone."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, command: SaveNoticeLog) -> None:
        """Persist the ledger. The caller commits."""
        await self._session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == command.run_id)
            .values(telegram_message_ids=dump_log(command.log))
        )
        await self._session.flush()
        stored = await self._session.get(AutopilotRunModel, command.run_id)
        if stored is not None:
            self._session.expire(stored)


def _event(row: EventOutboxModel) -> AutopilotOutboxEvent | None:
    run_id = _run_id(str(row.aggregate_id))
    if run_id is None:
        return None
    return AutopilotOutboxEvent(
        event_id=str(row.event_id),
        event_type=str(row.event_type),
        run_id=run_id,
        payload=_payload(row),
        created_at=_aware(cast(datetime | None, row.created_at)),
    )


def _payload(row: EventOutboxModel) -> Mapping[str, object]:
    raw = cast(object, row.payload)
    if isinstance(raw, dict):
        return cast(Mapping[str, object], raw)
    return {}


def _run_id(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
