"""Outbox window and notice-ledger writes for the Telegram dispatcher."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import ColumnElement, Tuple, and_, literal, select, tuple_, update
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
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    NotifyCursorModel,
)
from rag_backend.modules.autopilot.notify_constants import (
    NOTIFY_EVENT_TYPES,
    OUTBOX_SCAN_LIMIT,
)
from rag_backend.modules.autopilot.recovery_constants import (
    NOTIFY_CURSOR_NAME,
    NOTIFY_RESCAN_WINDOW_MINUTES,
)


class SqlAutopilotEventSource:
    """``content.autopilot.*`` rows after the cursor, oldest first.

    The cursor only moves past events the dispatcher has settled, so a busy
    outbox can never push an undelivered notice out of the scan window.
    ``created_at`` is the transaction start, so a row can commit behind the
    cursor; each scan re-reads a window behind it (QA r2 R5). The dispatcher
    skips re-read events its notice ledger already records. The window and
    the rows after the cursor are separate queries with their own limit, so a
    window full of settled rows can never starve new events (QA r3 Q1).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent(self) -> list[AutopilotOutboxEvent]:
        """The re-scan window behind the cursor, then the rows after it."""
        cursor = await self._session.get(NotifyCursorModel, NOTIFY_CURSOR_NAME)
        if cursor is None:
            return await self._scan(None)
        behind = await self._scan(_in_window(cursor))
        ahead = await self._scan(_after(cursor))
        return behind + ahead

    async def _scan(
        self, condition: ColumnElement[bool] | None
    ) -> list[AutopilotOutboxEvent]:
        query = (
            select(EventOutboxModel)
            .where(
                EventOutboxModel.aggregate_type == AGGREGATE_TYPE_AUTOPILOT_RUN,
                EventOutboxModel.event_type.in_(NOTIFY_EVENT_TYPES),
            )
            .order_by(EventOutboxModel.created_at.asc(), EventOutboxModel.event_id)
            .limit(OUTBOX_SCAN_LIMIT)
        )
        if condition is not None:
            query = query.where(condition)
        result = await self._session.execute(query)
        events = [_event(row) for row in result.scalars().all()]
        return [event for event in events if event is not None]

    async def advance(self, event: AutopilotOutboxEvent) -> None:
        """Move the cursor forward to ``event``; never back. The caller commits."""
        cursor = await self._session.get(NotifyCursorModel, NOTIFY_CURSOR_NAME)
        if cursor is None:
            self._session.add(
                NotifyCursorModel(
                    name=NOTIFY_CURSOR_NAME,
                    created_at=event.created_at,
                    event_id=event.event_id,
                )
            )
            await self._session.flush()
            return
        if not _is_ahead(event, cursor):
            return
        cursor.created_at = event.created_at
        cursor.event_id = event.event_id
        await self._session.flush()


def _position() -> Tuple:
    return tuple_(EventOutboxModel.created_at, EventOutboxModel.event_id)


def _cursor_position(cursor: NotifyCursorModel) -> Tuple:
    return tuple_(literal(_aware(cursor.created_at)), literal(cursor.event_id))


def _after(cursor: NotifyCursorModel) -> ColumnElement[bool]:
    return _position() > _cursor_position(cursor)


def _in_window(cursor: NotifyCursorModel) -> ColumnElement[bool]:
    window = timedelta(minutes=NOTIFY_RESCAN_WINDOW_MINUTES)
    return and_(
        EventOutboxModel.created_at > _aware(cursor.created_at) - window,
        _position() <= _cursor_position(cursor),
    )


def _is_ahead(event: AutopilotOutboxEvent, cursor: NotifyCursorModel) -> bool:
    position = (_aware(cursor.created_at), cursor.event_id)
    return (_aware(event.created_at), event.event_id) > position


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
