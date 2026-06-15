"""Unit tests for the transactional outbox + relay (AE-0130).

Gherkin: tests/features/transactional_outbox.feature

Covers the four AE-0130 behaviors:
* the outbox row is committed atomically with the state change (rollback => none);
* the relay publishes unpublished rows and marks them published;
* the relay is idempotent / at-least-once (re-run does not double-effect);
* the relayed payload is byte-identical to the legacy stream_event dict.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_FIELD_AGGREGATE_ID,
    EVENT_FIELD_AGGREGATE_TYPE,
    EVENT_FIELD_EVENT_ID,
    EVENT_FIELD_EVENT_TYPE,
    EVENT_FIELD_METADATA,
    EVENT_FIELD_PAYLOAD,
    EVENT_FIELD_TIMESTAMP,
    EVENT_FIELD_VERSION,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
    STREAM_CONTENT_EVENTS,
)
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.events import outbox_dispatch
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
    clear_memory_events,
    get_memory_events,
)
from rag_backend.infrastructure.events.outbox_relay import (
    _DEFAULT_BATCH_SIZE,
    OutboxRelay,
    OutboxRelayResult,
    outbox_stream_event,
)

_AGG_ID = "project-1"
_PAYLOAD: dict[str, object] = {"phase": "research"}
_METADATA: dict[str, object] = {"user_id": "user-1"}


@pytest.fixture(autouse=True)
def _clear_events() -> None:
    clear_memory_events()


@pytest_asyncio.fixture(autouse=True)
async def _clear_outbox(test_engine: AsyncEngine) -> None:
    """Clear any outbox rows committed by other tests on the shared engine.

    The session-scoped in-memory engine is shared across tests, and tests that
    commit through their own sessionmaker leave outbox rows behind; this scopes
    each relay test to only the rows it emits.
    """
    maker = async_sessionmaker(test_engine, class_=AsyncSession)
    async with maker() as session:
        await session.execute(delete(EventOutboxModel))
        await session.commit()


class _FailingPublisher:
    """Publisher whose publish always fails (transport outage)."""

    async def publish(self, stream: str, event: dict[str, object]) -> str:
        raise RuntimeError("redis unavailable")

    async def close(self) -> None:
        return None


async def _emit(db: AsyncSession) -> str:
    service = WorkflowEventService(MemoryEventPublisher())
    return await service.emit(
        db,
        event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
        aggregate_id=_AGG_ID,
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload=_PAYLOAD,
        metadata=_METADATA,
    )


async def _all_outbox(db: AsyncSession) -> list[EventOutboxModel]:
    result = await db.execute(select(EventOutboxModel))
    return list(result.scalars().all())


async def _unpublished_outbox(db: AsyncSession) -> list[EventOutboxModel]:
    result = await db.execute(
        select(EventOutboxModel).where(EventOutboxModel.published_at.is_(None))
    )
    return list(result.scalars().all())


async def _published_outbox(db: AsyncSession) -> list[EventOutboxModel]:
    result = await db.execute(
        select(EventOutboxModel).where(EventOutboxModel.published_at.is_not(None))
    )
    return list(result.scalars().all())


# Scenario: event persisted in the state transaction (atomic write).
@pytest.mark.asyncio
async def test_emit_writes_outbox_row_in_transaction(db_session: AsyncSession) -> None:
    """The outbox row exists in the open transaction after emit + flush."""
    event_id = await _emit(db_session)
    rows = await _all_outbox(db_session)
    assert len(rows) == 1
    assert rows[0].event_id == event_id
    assert rows[0].attempts == 0
    assert len(await _unpublished_outbox(db_session)) == 1
    assert await _published_outbox(db_session) == []


# Scenario: rollback => no outbox row (atomic with the state change).
@pytest.mark.asyncio
async def test_rollback_discards_outbox_row(db_session: AsyncSession) -> None:
    """A rolled-back transaction leaves no outbox row (and emits nothing)."""
    await _emit(db_session)
    await db_session.rollback()

    assert await _all_outbox(db_session) == []
    assert get_memory_events() == []


# Scenario: the relay publishes unpublished rows and marks them published.
@pytest.mark.asyncio
async def test_relay_publishes_and_marks_published(db_session: AsyncSession) -> None:
    """One relay pass publishes the unpublished row and stamps published_at."""
    event_id = await _emit(db_session)

    result = await OutboxRelay(MemoryEventPublisher()).run_once(db_session)

    assert result.published == 1
    assert result.failed == 0
    events = get_memory_events()
    assert len(events) == 1
    assert events[0][0] == STREAM_CONTENT_EVENTS
    assert events[0][1][EVENT_FIELD_EVENT_ID] == event_id

    assert len(await _published_outbox(db_session)) == 1
    assert await _unpublished_outbox(db_session) == []
    assert (await _all_outbox(db_session))[0].attempts == 1


# Scenario: relay is idempotent — re-run does not double-publish.
@pytest.mark.asyncio
async def test_relay_rerun_is_idempotent(db_session: AsyncSession) -> None:
    """Re-running the relay republishes nothing (single delivery on re-run)."""
    await _emit(db_session)
    relay = OutboxRelay(MemoryEventPublisher())

    first = await relay.run_once(db_session)
    second = await relay.run_once(db_session)

    assert first.published == 1
    assert second.published == 0  # already marked -> not re-selected
    assert len(get_memory_events()) == 1  # exactly one delivery total
    rows = await _all_outbox(db_session)
    assert rows[0].attempts == 1  # no extra attempt on the no-op pass


# Scenario: at-least-once — a failed publish leaves the row for the next pass.
@pytest.mark.asyncio
async def test_relay_retries_unpublished_after_failure(
    db_session: AsyncSession,
) -> None:
    """A transport failure leaves the row unpublished; a later pass delivers it."""
    event_id = await _emit(db_session)

    failed = await OutboxRelay(_FailingPublisher()).run_once(db_session)
    assert failed.published == 0
    assert failed.failed == 1
    assert len(await _unpublished_outbox(db_session)) == 1  # retried later
    assert (await _all_outbox(db_session))[0].attempts == 1  # failure counted

    retried = await OutboxRelay(MemoryEventPublisher()).run_once(db_session)
    assert retried.published == 1
    events = get_memory_events()
    assert len(events) == 1
    assert events[0][1][EVENT_FIELD_EVENT_ID] == event_id
    assert len(await _published_outbox(db_session)) == 1
    assert (await _all_outbox(db_session))[0].attempts == 2  # failed + successful


# Scenario: relayed payload is byte-identical to the legacy stream_event dict.
@pytest.mark.asyncio
async def test_relayed_payload_is_identical(db_session: AsyncSession) -> None:
    """The relayed event has the exact field set + values emit produced."""
    event_id = await _emit(db_session)
    rows = await _all_outbox(db_session)
    expected_timestamp = rows[0].event_timestamp
    # Parity with the legacy path: tz-aware ISO string (datetime.now(UTC).isoformat()),
    # dialect-proof — SQLite would strip the offset from a created_at round-trip.
    assert expected_timestamp.endswith("+00:00")

    await OutboxRelay(MemoryEventPublisher()).run_once(db_session)

    _stream, stream_event, _entry = get_memory_events()[0]
    assert set(stream_event.keys()) == {
        EVENT_FIELD_EVENT_ID,
        EVENT_FIELD_EVENT_TYPE,
        EVENT_FIELD_AGGREGATE_ID,
        EVENT_FIELD_AGGREGATE_TYPE,
        EVENT_FIELD_TIMESTAMP,
        EVENT_FIELD_VERSION,
        EVENT_FIELD_PAYLOAD,
        EVENT_FIELD_METADATA,
    }
    assert stream_event[EVENT_FIELD_EVENT_ID] == event_id
    assert stream_event[EVENT_FIELD_EVENT_TYPE] == EVENT_TYPE_PROJECT_PHASE_CHANGED
    assert stream_event[EVENT_FIELD_AGGREGATE_ID] == _AGG_ID
    assert stream_event[EVENT_FIELD_AGGREGATE_TYPE] == AGGREGATE_TYPE_PROJECT
    assert stream_event[EVENT_FIELD_TIMESTAMP] == expected_timestamp
    assert stream_event[EVENT_FIELD_VERSION] == 1
    assert stream_event[EVENT_FIELD_PAYLOAD] == _PAYLOAD
    assert stream_event[EVENT_FIELD_METADATA] == _METADATA


# Scenario: the relay reconstructs the payload from a single outbox row.
@pytest.mark.asyncio
async def test_outbox_stream_event_round_trip(db_session: AsyncSession) -> None:
    """outbox_stream_event mirrors what emit stored on the row."""
    event_id = await _emit(db_session)
    row = (await _all_outbox(db_session))[0]

    rebuilt = outbox_stream_event(row)
    assert rebuilt[EVENT_FIELD_EVENT_ID] == event_id
    assert rebuilt[EVENT_FIELD_PAYLOAD] == _PAYLOAD
    assert rebuilt[EVENT_FIELD_TIMESTAMP] == row.event_timestamp


def _patch_relay_loop(
    monkeypatch: pytest.MonkeyPatch, results: list[OutboxRelayResult]
) -> AsyncMock:
    """Patch relay_after_commit's session maker + OutboxRelay to a scripted relay.

    Returns the ``run_once`` AsyncMock so the test can assert how many passes the
    drain loop made before terminating.
    """
    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "rag_backend.infrastructure.database.config.get_session_maker",
        lambda: MagicMock(return_value=cm),
    )
    run_once = AsyncMock(side_effect=results)
    monkeypatch.setattr(
        outbox_dispatch, "OutboxRelay", lambda _publisher: MagicMock(run_once=run_once)
    )
    return run_once


# Scenario: the drain loop keeps going past a full batch until the backlog clears.
@pytest.mark.asyncio
async def test_relay_after_commit_drains_multiple_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full batch is followed by another pass; a non-full batch stops the loop."""
    run_once = _patch_relay_loop(
        monkeypatch,
        [
            OutboxRelayResult(published=_DEFAULT_BATCH_SIZE, failed=0),  # full -> more
            OutboxRelayResult(published=3, failed=0),  # non-full -> drained
        ],
    )

    await outbox_dispatch.relay_after_commit(MemoryEventPublisher())

    assert run_once.await_count == 2  # looped once more, then stopped


# Scenario: an all-failed full batch stops the loop (no infinite spin on outage).
@pytest.mark.asyncio
async def test_relay_after_commit_stops_on_no_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full batch with zero successes terminates immediately (published==0)."""
    run_once = _patch_relay_loop(
        monkeypatch,
        [OutboxRelayResult(published=0, failed=_DEFAULT_BATCH_SIZE)],
    )

    await outbox_dispatch.relay_after_commit(MemoryEventPublisher())

    assert run_once.await_count == 1  # no forward progress -> no second pass
