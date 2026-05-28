"""HTTP integration tests for editorial workflow SSE stream.

Feature: carousel_pipeline_consolidation.feature (@cp-sse-primary, @cp-sse-auth)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_ARTIFACT,
    SSE_EVENT_PHASE_CHANGE,
    SSE_EVENT_REVIEW_REQUIRED,
    publish_workflow_artifact,
    publish_workflow_sse_updates,
)
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    WORKFLOW_ARTIFACT_TYPE_OUTLINE,
)
from rag_backend.domain.models import UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    collect_hub_events_during,
    create_carousel,
    create_user,
    fetch_workflow_stream_snapshot,
    get_workflow_stream_status,
    seed_workflow_assigned_reviewer,
    seed_workflow_phase,
)


class TestEditorialWorkflowStreamHttp:
    """Scenarios: HTTP workflow SSE stream access and snapshots."""

    @pytest.mark.asyncio
    async def test_unauthenticated_workflow_stream_returns_401(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Unauthenticated workflow stream returns 401."""
        editor = await create_user("stream-anon@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

        status_code = await get_workflow_stream_status(client, project_id, headers={})

        assert status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_workflow_state_returns_401(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Unauthenticated workflow state returns 401."""
        editor = await create_user("state-anon@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)

        response = await client.get(f"/api/carousels/{project_id}/workflow/state")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_assigned_reviewer_cannot_subscribe_to_stream(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Editor without project access cannot subscribe to workflow stream."""
        owner = await create_user("stream-owner@example.com", UserRole.EDITOR)
        assigned = await create_user("stream-assigned@example.com", UserRole.EDITOR)
        outsider = await create_user("stream-outsider@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        status_code = await get_workflow_stream_status(
            client,
            project_id,
            headers=auth_header(outsider),
        )

        assert status_code == 403

    @pytest.mark.asyncio
    async def test_non_assigned_reviewer_cannot_read_workflow_state(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Editor without project access cannot read workflow state."""
        owner = await create_user("state-owner@example.com", UserRole.EDITOR)
        assigned = await create_user("state-assigned@example.com", UserRole.EDITOR)
        outsider = await create_user("state-outsider@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(outsider),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == ERR_CAROUSEL_TOOL_ACCESS_DENIED

    @pytest.mark.asyncio
    async def test_assigned_reviewer_can_open_workflow_stream(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Stream emits initial snapshot on connect."""
        owner = await create_user("stream-read-owner@example.com", UserRole.EDITOR)
        assigned = await create_user(
            "stream-read-assigned@example.com", UserRole.EDITOR
        )
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        status_code, events = await fetch_workflow_stream_snapshot(
            client,
            project_id,
            headers=auth_header(assigned),
        )

        assert status_code == 200
        assert any(event.get("event") == SSE_EVENT_PHASE_CHANGE for event in events)
        assert any(event.get("event") == SSE_EVENT_REVIEW_REQUIRED for event in events)

    @pytest.mark.asyncio
    async def test_live_hub_delivers_phase_change_on_workflow_publish(
        self, client: AsyncClient
    ) -> None:
        """Scenario: SSE delivers phase_change to live subscribers after workflow publish."""
        editor = await create_user("stream-publish@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

        async def publish_transition() -> None:
            await publish_workflow_sse_updates(
                project_id,
                {
                    "current_phase": PHASE_OUTLINE,
                    "phase_status": PHASE_STATUS_AWAITING_HUMAN,
                    "research_findings": [],
                    "outline": [{"slide_index": 1, "title": "Intro"}],
                    "slide_drafts": [],
                },
            )

        events = await collect_hub_events_during(
            project_id,
            publish_transition,
            expected_count=2,
        )

        assert any(event.get("event") == SSE_EVENT_PHASE_CHANGE for event in events)
        assert any(event.get("event") == SSE_EVENT_REVIEW_REQUIRED for event in events)

    @pytest.mark.asyncio
    async def test_workflow_stream_receives_artifact_event(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Artifact SSE events fan out to active workflow subscribers."""
        editor = await create_user("artifact-stream@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={"outline": [{"slide_index": 1, "title": "Intro"}]},
        )
        outline = [{"slide_index": 1, "title": "Updated intro"}]

        async def publish_outline_artifact() -> None:
            await publish_workflow_artifact(
                project_id,
                PHASE_OUTLINE,
                WORKFLOW_ARTIFACT_TYPE_OUTLINE,
                outline,
            )

        events = await collect_hub_events_during(project_id, publish_outline_artifact)

        artifact_events = [
            event for event in events if event.get("event") == SSE_EVENT_ARTIFACT
        ]
        assert artifact_events
        assert artifact_events[0]["artifact_type"] == WORKFLOW_ARTIFACT_TYPE_OUTLINE
        assert artifact_events[0]["data"] == outline
