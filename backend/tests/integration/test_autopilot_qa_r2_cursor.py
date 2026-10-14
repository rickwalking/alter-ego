"""Telegram notifier cursor re-scans a safety window (AE-0348 QA r2 R5).

The outbox ``created_at`` is the transaction start time, so a long
transaction can commit an event that sorts before the cursor. The event
source re-reads the window behind the cursor; the dispatcher's notice
ledger keeps a re-read event from being sent twice.

Gherkin: tests/features/autopilot_telegram_notify.feature
  Scenario: A notice committed behind the cursor is still delivered
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.infrastructure.models import NotifyCursorModel
from rag_backend.modules.autopilot.infrastructure.notice_source import (
    SqlAutopilotEventSource,
)
from rag_backend.modules.autopilot.notify_constants import OUTBOX_SCAN_LIMIT
from rag_backend.modules.autopilot.recovery_constants import (
    NOTIFY_CURSOR_NAME,
    NOTIFY_RESCAN_WINDOW_MINUTES,
)
from tests.integration.test_autopilot_qa_r1 import _outbox

_BASE = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)


def _at(minutes: float) -> datetime:
    return _BASE + timedelta(minutes=minutes)


# Scenario: A notice committed behind the cursor is still delivered
@pytest.mark.asyncio
async def test_event_committed_behind_the_cursor_is_read_again(
    db_session: AsyncSession,
) -> None:
    run_id = uuid4()
    source = SqlAutopilotEventSource(db_session)
    db_session.add(_outbox(run_id, _at(5)))
    await db_session.flush()
    [settled] = [e for e in await source.recent() if e.run_id == run_id]
    await source.advance(settled)

    # A long transaction that started at minute 3 commits only now.
    late = _outbox(run_id, _at(3))
    db_session.add(late)
    await db_session.flush()
    seen = [e.event_id for e in await source.recent() if e.run_id == run_id]

    assert late.event_id in seen


@pytest.mark.asyncio
async def test_events_older_than_the_window_are_not_read_again(
    db_session: AsyncSession,
) -> None:
    run_id = uuid4()
    source = SqlAutopilotEventSource(db_session)
    old = _outbox(run_id, _at(0))
    newest = _outbox(run_id, _at(NOTIFY_RESCAN_WINDOW_MINUTES + 5))
    db_session.add_all([old, newest])
    await db_session.flush()
    for event in await source.recent():
        await source.advance(event)

    seen = [e.event_id for e in await source.recent() if e.run_id == run_id]

    assert str(old.event_id) not in seen
    assert str(newest.event_id) in seen


@pytest.mark.asyncio
async def test_advancing_to_a_re_read_event_never_moves_the_cursor_back(
    db_session: AsyncSession,
) -> None:
    run_id = uuid4()
    source = SqlAutopilotEventSource(db_session)
    db_session.add_all([_outbox(run_id, _at(1)), _outbox(run_id, _at(4))])
    await db_session.flush()
    first, second = [e for e in await source.recent() if e.run_id == run_id]
    await source.advance(second)

    await source.advance(first)
    cursor = await db_session.get(NotifyCursorModel, NOTIFY_CURSOR_NAME)

    assert cursor is not None
    assert cursor.event_id == second.event_id


# Scenario: A full re-scan window never stalls the notifier
@pytest.mark.asyncio
async def test_new_event_is_read_past_a_window_full_of_settled_events(
    db_session: AsyncSession,
) -> None:
    run_id = uuid4()
    source = SqlAutopilotEventSource(db_session)
    settled = [
        _outbox(run_id, _at(index * 0.05)) for index in range(OUTBOX_SCAN_LIMIT + 50)
    ]
    db_session.add_all(settled)
    await db_session.flush()
    for _ in range(3):
        for event in await source.recent():
            await source.advance(event)

    fresh = _outbox(run_id, _at(9))
    db_session.add(fresh)
    await db_session.flush()
    seen = [e.event_id for e in await source.recent() if e.run_id == run_id]

    assert str(fresh.event_id) in seen
