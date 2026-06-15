"""Unit tests for WorkflowEventService post-commit publishing (AE-0074).

Gherkin: tests/features/workflow_event_ordering.feature
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.application.services.workflow_event_service import (
    WorkflowEventService,
    _AggregateQuery,
    drain_pending_publishes,
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
    SESSION_INFO_PENDING_EVENTS,
    STREAM_CONTENT_EVENTS,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
    clear_memory_events,
    get_memory_events,
)

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


async def _emit_phase_change(service: WorkflowEventService, db: AsyncSession) -> str:
    return await service.emit(
        db,
        event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
        aggregate_id="project-1",
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload={"phase": "research"},
        metadata={"user_id": "user-1"},
    )


@pytest.mark.asyncio
async def test_emit_publishes_only_after_commit(db_session: AsyncSession) -> None:
    """Scenario: Event published only after commit."""
    service = WorkflowEventService(MemoryEventPublisher())
    event_id = await _emit_phase_change(service, db_session)

    assert get_memory_events() == []  # nothing on the stream before commit

    await db_session.commit()
    await drain_pending_publishes()

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
async def test_rollback_publishes_nothing(db_session: AsyncSession) -> None:
    """Scenario: Rolled-back transaction publishes nothing."""
    service = WorkflowEventService(MemoryEventPublisher())
    await _emit_phase_change(service, db_session)

    await db_session.rollback()
    await drain_pending_publishes()

    assert get_memory_events() == []
    # The rollback listener must clear the queue, not merely skip publish
    assert SESSION_INFO_PENDING_EVENTS not in db_session.sync_session.info
    entries = await service.list_for_aggregate(
        db_session,
        _AggregateQuery(
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            aggregate_id="project-1",
        ),
    )
    assert entries == []


@pytest.mark.asyncio
async def test_commit_after_rollback_does_not_publish_stale_events(
    db_session: AsyncSession,
) -> None:
    """Scenario: Rolled-back transaction publishes nothing (stale-queue edge)."""
    service = WorkflowEventService(MemoryEventPublisher())
    await _emit_phase_change(service, db_session)
    await db_session.rollback()

    await db_session.commit()  # a later, unrelated commit on the same session
    await drain_pending_publishes()

    assert get_memory_events() == []


@pytest.mark.asyncio
async def test_publish_failure_after_commit_does_not_raise(
    db_session: AsyncSession,
) -> None:
    """Scenario: Publish failure after commit does not break the request."""
    service = WorkflowEventService(_FailingPublisher())
    event_id = await _emit_phase_change(service, db_session)

    await db_session.commit()
    with capture_logs() as logs:
        await drain_pending_publishes()  # must swallow the transport failure

    assert get_memory_events() == []
    failures = [
        entry for entry in logs if entry["event"] == "workflow_event_publish_failed"
    ]
    assert len(failures) == 1
    assert failures[0]["event_id"] == event_id  # failure logged with event ID
    entries = await service.list_for_aggregate(
        db_session,
        _AggregateQuery(
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            aggregate_id="project-1",
        ),
    )
    assert len(entries) == 1  # audit row survives a failed publish


@pytest.mark.asyncio
async def test_second_commit_does_not_republish(db_session: AsyncSession) -> None:
    """Scenario: Event published only after commit (no duplicate on re-commit)."""
    service = WorkflowEventService(MemoryEventPublisher())
    await _emit_phase_change(service, db_session)

    await db_session.commit()
    await drain_pending_publishes()
    await db_session.commit()  # a later, event-free commit on the same session
    await drain_pending_publishes()

    assert len(get_memory_events()) == 1  # queue was drained, not re-read


@pytest.mark.asyncio
async def test_event_payload_shape_is_unchanged(db_session: AsyncSession) -> None:
    """Scenario: Event published only after commit (payload-shape fixture)."""
    service = WorkflowEventService(MemoryEventPublisher())
    event_id = await _emit_phase_change(service, db_session)
    await db_session.commit()
    await drain_pending_publishes()

    stream, stream_event, _entry = get_memory_events()[0]
    assert stream == STREAM_CONTENT_EVENTS
    assert set(stream_event.keys()) == _EXPECTED_EVENT_FIELDS
    assert stream_event[EVENT_FIELD_EVENT_ID] == event_id
    assert stream_event[EVENT_FIELD_EVENT_TYPE] == EVENT_TYPE_PROJECT_PHASE_CHANGED
    assert stream_event[EVENT_FIELD_VERSION] == 1
    assert stream_event[EVENT_FIELD_PAYLOAD] == {"phase": "research"}
    assert stream_event[EVENT_FIELD_METADATA] == {"user_id": "user-1"}
