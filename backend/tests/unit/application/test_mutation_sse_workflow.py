"""Manual mutation tests for SSE workflow modules.

Feature: carousel_pipeline_consolidation.feature (@cp-sse-primary)
Run with: uv run pytest tests/unit/application/test_mutation_sse_workflow.py -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_KEEPALIVE,
    SSE_EVENT_PROGRESS,
    SSE_EVENT_REVIEW_REQUIRED,
    EventParams,
    build_progress_event,
    build_review_required_event,
    publish_workflow_sse_updates,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    SSE_EVENT_KEY,
    WorkflowSseHub,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
)


@pytest.mark.unit
class TestWorkflowSseMutationResilience:
    """Mutation-style assertions for SSE hub and publish payloads."""

    def test_mutation_nested_progress_payload_required(self) -> None:
        """Kills mutants that drop nested phase_progress."""
        nested = build_progress_event(
            "project-1", "images", {"current": 4, "total": 10}
        )
        assert isinstance(nested.get("phase_progress"), dict)
        assert nested["phase_progress"]["current"] == 4

    async def test_mutation_keepalive_marker_is_distinct_from_progress(self) -> None:
        """Kills mutants that treat keepalive as progress."""
        hub = WorkflowSseHub()
        received: list[dict[str, object]] = []

        async def consume() -> None:
            async for event in hub.listen("project-1", keepalive_seconds=0.01):
                received.append(event)
                break

        await asyncio.wait_for(consume(), timeout=0.5)
        assert received[0][SSE_EVENT_KEY] == SSE_EVENT_KEEPALIVE
        assert received[0][SSE_EVENT_KEY] != SSE_EVENT_PROGRESS

    async def test_mutation_review_required_emitted_at_human_gate(self) -> None:
        """Kills mutants that skip review_required publish."""
        mock_hub = AsyncMock()
        state = {
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "research_findings": [{"title": "Finding"}],
            "outline": [],
            "slide_drafts": [],
        }

        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=mock_hub,
        ):
            await publish_workflow_sse_updates("project-1", state)

        event_types = [
            call.args[1]["event"] for call in mock_hub.publish.await_args_list
        ]
        assert SSE_EVENT_REVIEW_REQUIRED in event_types

    def test_mutation_review_required_includes_gate_payload(self) -> None:
        """Kills mutants that omit gate payload."""
        event = build_review_required_event(
            EventParams(project_id="project-1", phase=PHASE_RESEARCH),
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            gate_payload={"current_phase": PHASE_RESEARCH, "outline": []},
        )
        assert isinstance(event.get("gate_payload"), dict)
