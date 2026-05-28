"""Unit tests for in-process workflow SSE hub.

Feature: carousel_pipeline_consolidation.feature (@cp-sse-primary)
"""

from __future__ import annotations

import asyncio

import pytest

from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_KEEPALIVE,
    SSE_EVENT_PROGRESS,
    build_progress_event,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    SSE_EVENT_KEY,
    WorkflowSseHub,
    reset_workflow_sse_hub,
)


@pytest.fixture(autouse=True)
def _reset_workflow_sse_hub() -> None:
    reset_workflow_sse_hub()
    yield
    reset_workflow_sse_hub()


@pytest.mark.unit
class TestWorkflowSseHub:
    """Scenarios: live SSE progress fan-out."""

    async def test_publish_delivers_event_to_subscriber(self) -> None:
        """Scenario: Live progress events arrive during long resume without state polling."""
        hub = WorkflowSseHub()
        project_id = "project-1"
        received: list[dict[str, object]] = []

        async def consume() -> None:
            async for event in hub.listen(project_id, keepalive_seconds=0.05):
                if event.get(SSE_EVENT_KEY) == SSE_EVENT_KEEPALIVE:
                    continue
                received.append(event)
                break

        consumer = asyncio.create_task(consume())
        await asyncio.sleep(0)
        await hub.publish(
            project_id,
            build_progress_event(
                project_id,
                "images",
                {"current": 3, "total": 10, "label": "Generating slide 3 of 10"},
            ),
        )
        await asyncio.wait_for(consumer, timeout=1.0)

        assert received[0]["event"] == SSE_EVENT_PROGRESS
        progress = received[0]["phase_progress"]
        assert isinstance(progress, dict)
        assert progress["current"] == 3
        assert progress["total"] == 10

    async def test_multiple_subscribers_receive_same_event(self) -> None:
        """Scenario: Multiple SSE subscribers receive the same progress event."""
        hub = WorkflowSseHub()
        project_id = "project-1"
        first: list[dict[str, object]] = []
        second: list[dict[str, object]] = []

        async def consume_one(target: list[dict[str, object]]) -> None:
            async for event in hub.listen(project_id, keepalive_seconds=0.05):
                if event.get(SSE_EVENT_KEY) == SSE_EVENT_KEEPALIVE:
                    continue
                target.append(event)
                break

        task_one = asyncio.create_task(consume_one(first))
        task_two = asyncio.create_task(consume_one(second))
        await asyncio.sleep(0)
        payload = build_progress_event(project_id, "images", {"current": 1, "total": 2})
        await hub.publish(project_id, payload)
        await asyncio.wait_for(asyncio.gather(task_one, task_two), timeout=1.0)

        assert first == second
        assert first[0]["phase_progress"] == {"current": 1, "total": 2}

    async def test_listen_emits_keepalive_marker_on_idle(self) -> None:
        """Scenario: Stream sends keepalive without repeating progress at human gate."""
        hub = WorkflowSseHub()
        project_id = "project-1"
        received: list[dict[str, object]] = []

        async def consume() -> None:
            async for event in hub.listen(project_id, keepalive_seconds=0.01):
                received.append(event)
                if len(received) >= 1:
                    break

        await asyncio.wait_for(consume(), timeout=0.5)
        assert received[0][SSE_EVENT_KEY] == SSE_EVENT_KEEPALIVE

    async def test_rejects_subscribers_beyond_project_cap(self) -> None:
        """Scenario: SSE hub rejects connections beyond the per-project cap."""
        from rag_backend.application.services.carousel.editorial_workflow_support import (
            WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT,
        )
        from rag_backend.application.services.carousel.workflow_sse_hub import (
            WorkflowSseSubscriberLimitError,
        )

        hub = WorkflowSseHub()
        project_id = "project-cap"
        queues: list[asyncio.Task[None]] = []

        async def hold_connection() -> None:
            async for _event in hub.listen(project_id, keepalive_seconds=30):
                await asyncio.sleep(3600)

        for _ in range(WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT):
            queues.append(asyncio.create_task(hold_connection()))
        await asyncio.sleep(0)

        with pytest.raises(WorkflowSseSubscriberLimitError):
            async for _event in hub.listen(project_id, keepalive_seconds=0.05):
                break

        for task in queues:
            task.cancel()
        await asyncio.gather(*queues, return_exceptions=True)
        assert hub.subscriber_count(project_id) == 0

    async def test_parallel_progress_events_are_monotonic(self) -> None:
        """Scenario: Multiple progress events increase monotonically during parallel work."""
        hub = WorkflowSseHub()
        project_id = "project-progress"
        received: list[dict[str, object]] = []

        async def consume() -> None:
            async for event in hub.listen(project_id, keepalive_seconds=0.05):
                if event.get(SSE_EVENT_KEY) == SSE_EVENT_KEEPALIVE:
                    continue
                if event.get("event") == SSE_EVENT_PROGRESS:
                    received.append(event)
                    if len(received) >= 3:
                        break

        consumer = asyncio.create_task(consume())
        await asyncio.sleep(0)
        for current in (1, 2, 3):
            await hub.publish(
                project_id,
                build_progress_event(
                    project_id,
                    "images",
                    {"current": current, "total": 10},
                ),
            )
        await asyncio.wait_for(consumer, timeout=1.0)

        currents: list[int] = []
        for event in received:
            progress = event.get("phase_progress")
            assert isinstance(progress, dict)
            currents.append(int(progress["current"]))
        assert currents == [1, 2, 3]
