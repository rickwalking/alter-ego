"""Unit tests for WorkflowEventService (WF-001, WF-004)."""

# Gherkin: tests/features/phase3_workflow_collaboration.feature
# Scenario: Emit phase change event

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
    clear_memory_events,
    get_memory_events,
)


@pytest.fixture(autouse=True)
def _clear_events() -> None:
    clear_memory_events()


@pytest.mark.asyncio
async def test_emit_publishes_and_persists_audit(db_session: AsyncSession) -> None:
    """Emit should publish to stream and write audit log."""
    service = WorkflowEventService(MemoryEventPublisher())
    event_id = await service.emit(
        db_session,
        event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
        aggregate_id="project-1",
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload={"phase": "research"},
        metadata={"user_id": "user-1"},
    )
    await db_session.commit()

    events = get_memory_events()
    assert len(events) == 1
    assert events[0][1]["event_id"] == event_id

    entries = await service.list_for_aggregate(
        db_session, aggregate_type=AGGREGATE_TYPE_PROJECT, aggregate_id="project-1"
    )
    assert len(entries) == 1
    assert entries[0].event_type == EVENT_TYPE_PROJECT_PHASE_CHANGED
