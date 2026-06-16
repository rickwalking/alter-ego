"""Integration tests for the outbox after-commit relay path (AE-0130).

Gherkin: tests/features/transactional_outbox.feature

The unit suites drive ``OutboxRelay.run_once`` directly on the test session. These
tests exercise the *production* path end to end: ``emit`` → ``session.commit()`` →
the SQLAlchemy ``after_commit`` listener → ``relay_after_commit`` opening a FRESH
session via ``get_session_maker`` → exactly one Redis publish, drained through
``drain_pending_publishes``. They also prove a rolled-back emit followed by an
unrelated commit publishes nothing (no stale queued events survive a rollback).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.workflow_event_service import (
    WorkflowEventService,
    drain_pending_publishes,
)
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_FIELD_EVENT_ID,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
    STREAM_CONTENT_EVENTS,
)
from rag_backend.infrastructure.database import config as db_config
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
    clear_memory_events,
    get_memory_events,
)

_AGG_ID = "project-after-commit-1"
_PAYLOAD: dict[str, object] = {"phase": "research"}
_METADATA: dict[str, object] = {"user_id": "user-1"}


@pytest.fixture(autouse=True)
def _clear_events() -> None:
    clear_memory_events()


@pytest_asyncio.fixture
async def committing_maker(
    test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> async_sessionmaker[AsyncSession]:
    """A real (committing) sessionmaker bound to the shared in-memory engine.

    Also points the global ``c_engine`` at the test engine so the after-commit
    relay's fresh ``get_session_maker`` session reads the same in-memory database.
    """
    monkeypatch.setattr(db_config, "c_engine", test_engine)
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as cleanup:
        await cleanup.execute(delete(EventOutboxModel))
        await cleanup.commit()
    return maker


async def _emit(session: AsyncSession) -> str:
    service = WorkflowEventService(MemoryEventPublisher())
    return await service.emit(
        session,
        event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
        aggregate_id=_AGG_ID,
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload=_PAYLOAD,
        metadata=_METADATA,
    )


# Scenario: a committed emit is published exactly once via the after-commit relay.
@pytest.mark.asyncio
async def test_commit_relays_exactly_once_via_after_commit(
    committing_maker: async_sessionmaker[AsyncSession],
) -> None:
    """emit + commit triggers the fresh-session relay; exactly one delivery."""
    async with committing_maker() as session:
        event_id = await _emit(session)
        assert get_memory_events() == []  # nothing before commit
        await session.commit()

    await drain_pending_publishes()

    events = get_memory_events()
    assert len(events) == 1  # the after-commit relay published exactly once
    stream, stream_event, _entry = events[0]
    assert stream == STREAM_CONTENT_EVENTS
    assert stream_event[EVENT_FIELD_EVENT_ID] == event_id

    async with committing_maker() as verify:
        published = await verify.execute(
            select(EventOutboxModel).where(EventOutboxModel.published_at.is_not(None))
        )
        assert len(list(published.scalars().all())) == 1  # row marked published


# Scenario: a rolled-back emit followed by an unrelated commit publishes nothing.
@pytest.mark.asyncio
async def test_rollback_then_commit_does_not_publish_stale_events(
    committing_maker: async_sessionmaker[AsyncSession],
) -> None:
    """after_rollback drops the queue, so a later commit relays no stale event."""
    async with committing_maker() as session:
        await _emit(session)
        await session.rollback()  # discards the queued relay + the outbox row
        await session.commit()  # an unrelated commit must not relay anything

    await drain_pending_publishes()

    assert get_memory_events() == []  # no stale delivery
    async with committing_maker() as verify:
        rows = await verify.execute(select(EventOutboxModel))
        assert list(rows.scalars().all()) == []  # rolled back -> no durable row
