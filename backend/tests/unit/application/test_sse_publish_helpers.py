"""Unit tests for workflow SSE publish helpers.

Feature: carousel_pipeline_consolidation.feature (@cp-sse-primary)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_ARTIFACT,
    SSE_EVENT_PHASE_CHANGE,
    SSE_EVENT_PROGRESS,
    SSE_EVENT_REVIEW_REQUIRED,
    EventParams,
    PublishParams,
    build_artifact_event,
    build_progress_event,
    publish_workflow_artifact,
    publish_workflow_phase_change,
    publish_workflow_progress,
    publish_workflow_review_required,
    publish_workflow_sse_updates,
    resolve_workflow_sse_error_message,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    ERR_WORKFLOW_PHASE_FAILED,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    WORKFLOW_ARTIFACT_TYPE_OUTLINE,
    WORKFLOW_ERROR_KEY,
)


@pytest.mark.unit
class TestWorkflowSsePublishHelpers:
    """Scenarios: SSE publish helpers fan out through the hub."""

    async def test_publish_workflow_progress_uses_nested_payload(self) -> None:
        hub = AsyncMock()
        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=hub,
        ):
            await publish_workflow_progress(
                "project-1",
                "images",
                {"current": 2, "total": 5},
            )

        hub.publish.assert_awaited_once()
        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_PROGRESS
        assert event["phase_progress"] == {"current": 2, "total": 5}

    async def test_publish_workflow_phase_change(self) -> None:
        hub = AsyncMock()
        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=hub,
        ):
            await publish_workflow_phase_change(
                "project-1",
                PHASE_RESEARCH,
                PHASE_STATUS_AWAITING_HUMAN,
            )

        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_PHASE_CHANGE

    async def test_publish_workflow_review_required(self) -> None:
        hub = AsyncMock()
        state = {
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "research_findings": [{"title": "Finding"}],
            "outline": [],
            "slide_drafts": [],
        }
        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=hub,
        ):
            await publish_workflow_review_required("project-1", state)

        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_REVIEW_REQUIRED
        assert isinstance(event["gate_payload"], dict)

    async def test_publish_workflow_sse_updates_at_human_gate(self) -> None:
        hub = AsyncMock()
        state = {
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "research_findings": [],
            "outline": [],
            "slide_drafts": [],
        }
        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=hub,
        ):
            await publish_workflow_sse_updates("project-1", state)

        assert hub.publish.await_count == 2
        event_types = [call.args[1]["event"] for call in hub.publish.await_args_list]
        assert SSE_EVENT_PHASE_CHANGE in event_types
        assert SSE_EVENT_REVIEW_REQUIRED in event_types

    async def test_publish_workflow_sse_updates_on_failure(self) -> None:
        hub = AsyncMock()
        state = {
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_FAILED,
            "error_message": "Internal stack trace: boom",
        }
        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=hub,
        ):
            await publish_workflow_sse_updates("project-1", state)

        error_events = [
            call.args[1]
            for call in hub.publish.await_args_list
            if call.args[1]["event"] == "error"
        ]
        assert error_events
        assert error_events[0]["message"] == ERR_WORKFLOW_PHASE_FAILED

    async def test_publish_workflow_artifact(self) -> None:
        hub = AsyncMock()
        outline = [{"slide_index": 1, "title": "Intro"}]
        with patch(
            "rag_backend.application.services.carousel.workflow_sse_hub.get_workflow_sse_hub",
            return_value=hub,
        ):
            await publish_workflow_artifact(
                PublishParams(project_id="project-1", phase=PHASE_RESEARCH),
                artifact_type=WORKFLOW_ARTIFACT_TYPE_OUTLINE,
                data=outline,
            )

        event = hub.publish.await_args.args[1]
        assert event["event"] == SSE_EVENT_ARTIFACT
        assert event["artifact_type"] == WORKFLOW_ARTIFACT_TYPE_OUTLINE
        assert event["data"] == outline

    def test_resolve_workflow_sse_error_message_maps_internal_errors(self) -> None:
        assert (
            resolve_workflow_sse_error_message({"error_message": "Internal boom"})
            == ERR_WORKFLOW_PHASE_FAILED
        )
        assert (
            resolve_workflow_sse_error_message({WORKFLOW_ERROR_KEY: ERR_INVALID_JSON})
            == ERR_INVALID_JSON
        )

    def test_build_artifact_event_shape(self) -> None:
        payload = build_artifact_event(
            EventParams(project_id="project-1", phase=PHASE_RESEARCH),
            artifact_type=WORKFLOW_ARTIFACT_TYPE_OUTLINE,
            data=[{"title": "Intro"}],
        )
        assert payload["event"] == SSE_EVENT_ARTIFACT
        assert payload["artifact_type"] == WORKFLOW_ARTIFACT_TYPE_OUTLINE

    def test_build_progress_event_shape(self) -> None:
        payload = build_progress_event(
            "project-1", "images", {"current": 1, "total": 3}
        )
        assert payload["phase_progress"]["current"] == 1
