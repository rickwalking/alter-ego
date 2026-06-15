"""Unit tests for WorkflowEventService via the transactional outbox (AE-0130).

Gherkin: tests/features/workflow_event_ordering.feature,
         tests/features/transactional_outbox.feature

``emit`` writes the audit + outbox rows in the same transaction; the relay is the
sole Redis publisher (selecting unpublished rows, publishing, marking them). These
tests drive the relay explicitly against the connection-bound test session (the
after-commit listener relays against a fresh session, which is exercised by the
file-backed publishing safety net instead).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

from rag_backend.application.services.workflow_event_service import (
    WorkflowEventService,
    _AggregateQuery,
)
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
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
    clear_memory_events,
    get_memory_events,
)
from rag_backend.infrastructure.events.outbox_relay import OutboxRelay

_EXPECTED_EVENT_FIELDS = {
    EVENT_FIELD_EVENT_ID,
    EVENT_FIELD_EVENT_TYPE,
    EVENT_FIELD_AGGREGATE_ID,
    EVENT_FIELD_AGGREGATE_TYPE,
    EVENT_FIELD_TIMESTAMP,
    EVENT_FIELD_VERSION,
    EVENT_FIELD_PAYLOAD,
    EVENT_FIELD_METADATA,
}


class _FailingPublisher:
    """Publisher stub whose publish always fails (transport outage)."""

    async def publish(self, stream: str, event: dict[str, object]) -> str:
        raise RuntimeError("redis unavailable")

    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _clear_events() -> None:
    clear_memory_events()


@pytest_asyncio.fixture(autouse=True)
async def _clear_outbox(test_engine: AsyncEngine) -> None:
    """Clear outbox rows committed by other tests on the shared in-memory engine."""
    maker = async_sessionmaker(test_engine, class_=AsyncSession)
    async with maker() as session:
        await session.execute(delete(EventOutboxModel))
        await session.commit()


async def _emit_phase_change(service: WorkflowEventService, db: AsyncSession) -> str:
    return await service.emit(
        db,
        event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
        aggregate_id="project-1",
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload={"phase": "research"},
        metadata={"user_id": "user-1"},
    )


async def _outbox_rows(db: AsyncSession) -> list[EventOutboxModel]:
    result = await db.execute(select(EventOutboxModel))
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_emit_does_not_publish_before_relay(db_session: AsyncSession) -> None:
    """Scenario: Event published only via the relay, not by emit itself."""
    service = WorkflowEventService(MemoryEventPublisher())
    event_id = await _emit_phase_change(service, db_session)

    assert get_memory_events() == []  # emit never publishes directly

    await OutboxRelay(MemoryEventPublisher()).run_once(db_session)

    events = get_memory_events()
    assert len(events) == 1
    assert events[0][0] == STREAM_CONTENT_EVENTS
    assert events[0][1][EVENT_FIELD_EVENT_ID] == event_id

    entries = await service.list_for_aggregate(
        db_session,
        _AggregateQuery(
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            aggregate_id="project-1",
        ),
    )
    assert len(entries) == 1
    assert entries[0].event_type == EVENT_TYPE_PROJECT_PHASE_CHANGED


@pytest.mark.asyncio
async def test_rollback_discards_audit_and_outbox(db_session: AsyncSession) -> None:
    """Scenario: Rolled-back transaction persists nothing (audit + outbox)."""
    service = WorkflowEventService(MemoryEventPublisher())
    await _emit_phase_change(service, db_session)

    await db_session.rollback()

    assert await _outbox_rows(db_session) == []
    entries = await service.list_for_aggregate(
        db_session,
        _AggregateQuery(
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            aggregate_id="project-1",
        ),
    )
    assert entries == []


@pytest.mark.asyncio
async def test_failed_relay_keeps_audit_and_outbox(db_session: AsyncSession) -> None:
    """Scenario: Publish failure does not destroy the durable rows (replayable)."""
    service = WorkflowEventService(MemoryEventPublisher())
    event_id = await _emit_phase_change(service, db_session)

    with capture_logs() as logs:
        result = await OutboxRelay(_FailingPublisher()).run_once(db_session)

    assert result.failed == 1
    assert get_memory_events() == []
    failures = [
        entry for entry in logs if entry["event"] == "outbox_relay_publish_failed"
    ]
    assert len(failures) == 1
    assert failures[0]["event_id"] == event_id

    rows = await _outbox_rows(db_session)
    assert len(rows) == 1  # outbox row survives a failed publish -> replayable
    unpublished = await db_session.execute(
        select(EventOutboxModel).where(EventOutboxModel.published_at.is_(None))
    )
    assert len(list(unpublished.scalars().all())) == 1  # still unpublished
    entries = await service.list_for_aggregate(
        db_session,
        _AggregateQuery(
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            aggregate_id="project-1",
        ),
    )
    assert len(entries) == 1  # audit row survives a failed publish


@pytest.mark.asyncio
async def test_relay_rerun_does_not_republish(db_session: AsyncSession) -> None:
    """Scenario: No duplicate delivery when the relay runs again."""
    service = WorkflowEventService(MemoryEventPublisher())
    await _emit_phase_change(service, db_session)
    relay = OutboxRelay(MemoryEventPublisher())

    await relay.run_once(db_session)
    await relay.run_once(db_session)  # a later, no-op relay pass

    assert len(get_memory_events()) == 1  # marked rows are not re-selected


@pytest.mark.asyncio
async def test_event_payload_shape_is_unchanged(db_session: AsyncSession) -> None:
    """Scenario: Relayed payload matches the legacy stream_event shape + values."""
    service = WorkflowEventService(MemoryEventPublisher())
    event_id = await _emit_phase_change(service, db_session)
    await OutboxRelay(MemoryEventPublisher()).run_once(db_session)

    stream, stream_event, _entry = get_memory_events()[0]
    assert stream == STREAM_CONTENT_EVENTS
    assert set(stream_event.keys()) == _EXPECTED_EVENT_FIELDS
    assert stream_event[EVENT_FIELD_EVENT_ID] == event_id
    assert stream_event[EVENT_FIELD_EVENT_TYPE] == EVENT_TYPE_PROJECT_PHASE_CHANGED
    assert stream_event[EVENT_FIELD_VERSION] == 1
    assert stream_event[EVENT_FIELD_PAYLOAD] == {"phase": "research"}
    assert stream_event[EVENT_FIELD_METADATA] == {"user_id": "user-1"}
