"""Carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models import UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    drain_background_tasks,
    get_lock_version,
    seed_workflow_phase,
    set_project_phase_progress,
)


class TestWorkflowPhaseGateArtifacts:
    """Scenarios: design and images gate artifact fields."""

    @pytest.mark.asyncio
    async def test_design_gate_state_includes_design_applied(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Design gate includes design_applied and preview metadata."""
        editor = await create_user("design-gate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_DESIGN,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={"design_applied": True},
        )

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )

        assert response.status_code == 200
        assert response.json()["design_applied"] is True

    @pytest.mark.asyncio
    async def test_images_gate_state_includes_image_assets(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Images gate includes image asset references."""
        editor = await create_user("images-gate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_IMAGES,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={"image_assets": ["/tmp/images/slide_1.jpg"]},
        )

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )

        assert response.status_code == 200
        assert response.json()["image_assets"]


class TestStructuredFeedbackSecurity:
    """Scenario: Structured feedback is gated to final review only."""

    @pytest.mark.asyncio
    async def test_structured_feedback_rejected_outside_final_review(
        self, client: AsyncClient
    ) -> None:
        editor = await create_user("structured-gate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_CONTENT,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={"slide_drafts": [{"draft_text": "Body"}]},
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "feedback": "Try again",
                "expected_version": version,
                "structured_feedback": {"target_phase": PHASE_CONTENT},
            },
            headers=auth_header(editor),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY


class TestFinalReviewGateArtifacts:
    """Scenario: Final review gate includes blog caption and rubric scores."""

    @pytest.mark.asyncio
    async def test_final_review_state_includes_caption_blog_and_rubric(
        self, client: AsyncClient
    ) -> None:
        editor = await create_user("final-artifacts@example.com", UserRole.EDITOR)
        project_id = await create_carousel(
            editor,
            is_public=False,
            blog_markdown="# Draft blog\n\nBody",
        )
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_FINAL_REVIEW,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "caption": "Draft caption for Instagram",
                "blog_markdown": "# Draft blog\n\nBody",
                "rubric_scores": {"voice_match": 88, "clarity": 90},
            },
        )

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["caption"]
        assert payload["blog_markdown"]
        assert payload["rubric_scores"]


class TestEditorialWorkflowStream:
    """Scenarios: unified workflow progress streaming."""

    @pytest.mark.asyncio
    async def test_stream_emits_progress_during_in_progress(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Stream emits progress during in_progress phase."""
        from rag_backend.application.services.carousel.editorial_workflow_service import (
            EditorialWorkflowService,
        )
        from rag_backend.application.services.carousel.editorial_workflow_support import (
            SSE_EVENT_PROGRESS,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        editor = await create_user("stream-progress@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_IMAGES,
            phase_status=PHASE_STATUS_IN_PROGRESS,
        )
        await set_project_phase_progress(
            project_id,
            {
                "phase": "images",
                "message": "Generating slide 2 of 5",
                "percent": 40,
            },
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            service = EditorialWorkflowService(
                llm=AsyncMock(),
                checkpointer=client.app.state.carousel_checkpointer,  # type: ignore[attr-defined]
                event_service=AsyncMock(),
                image_registry=None,
            )
            events: list[dict[str, object]] = []
            async for payload in service.stream_phase_updates(
                project_id,
                phase_progress={
                    "phase": "images",
                    "message": "Generating slide 2 of 5",
                    "percent": 40,
                },
            ):
                events.append(payload)
                if len(events) >= 2:
                    break

        assert len(events) >= 2
        progress_event = next(
            event for event in events if event.get("event") == SSE_EVENT_PROGRESS
        )
        phase_progress = progress_event.get("phase_progress")
        assert isinstance(phase_progress, dict)
        assert phase_progress.get("message") == "Generating slide 2 of 5"
        assert phase_progress.get("percent") == 40

    @pytest.mark.asyncio
    async def test_stream_skips_idle_progress_at_awaiting_human(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Stream does not emit legacy idle pending loops."""
        from rag_backend.application.services.carousel.editorial_workflow_service import (
            EditorialWorkflowService,
        )
        from rag_backend.application.services.carousel.editorial_workflow_support import (
            SSE_EVENT_PHASE_CHANGE,
            SSE_EVENT_PROGRESS,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        editor = await create_user("stream-idle@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_DESIGN,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={"design_applied": True},
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            service = EditorialWorkflowService(
                llm=AsyncMock(),
                checkpointer=client.app.state.carousel_checkpointer,  # type: ignore[attr-defined]
                event_service=AsyncMock(),
                image_registry=None,
            )
            events: list[dict[str, object]] = []
            async for payload in service.stream_phase_updates(project_id):
                events.append(payload)
                break

        assert any(event.get("event") == SSE_EVENT_PHASE_CHANGE for event in events)
        assert not any(event.get("event") == SSE_EVENT_PROGRESS for event in events)

    @pytest.mark.asyncio
    async def test_stream_emits_review_required_on_connect(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Stream emits review_required when awaiting human approval."""
        from rag_backend.application.services.carousel.editorial_workflow_service import (
            EditorialWorkflowService,
        )
        from rag_backend.application.services.carousel.editorial_workflow_support import (
            SSE_EVENT_PHASE_CHANGE,
            SSE_EVENT_REVIEW_REQUIRED,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        editor = await create_user("stream-review@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            service = EditorialWorkflowService(
                llm=AsyncMock(),
                checkpointer=client.app.state.carousel_checkpointer,  # type: ignore[attr-defined]
                event_service=AsyncMock(),
                image_registry=None,
            )
            events: list[dict[str, object]] = []
            async for payload in service.stream_phase_updates(project_id):
                events.append(payload)
                if len(events) >= 2:
                    break

        assert any(event.get("event") == SSE_EVENT_PHASE_CHANGE for event in events)
        assert any(event.get("event") == SSE_EVENT_REVIEW_REQUIRED for event in events)

    @pytest.mark.asyncio
    async def test_workflow_state_reads_are_not_rate_limited(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Rapid workflow state reads do not return 429."""
        editor = await create_user("state-rate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

        for _ in range(20):
            response = await client.get(
                f"/api/carousels/{project_id}/workflow/state",
                headers=auth_header(editor),
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_phase_progress_persists_on_project_row(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Phase progress persists on project row for reload."""
        editor = await create_user("persist-progress@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_DESIGN,
            phase_status=PHASE_STATUS_IN_PROGRESS,
        )
        snapshot = {
            "phase": "design",
            "message": "Applying design tokens",
            "percent": 75,
        }
        await set_project_phase_progress(project_id, snapshot)

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )

        assert response.status_code == 200
        assert response.json()["phase_progress"] == snapshot


class TestReviseThenApproveOutline:
    """Scenario: Revise after prior revise still accepts approve."""

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator.resume",
        new_callable=AsyncMock,
    )
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator.get_state",
        new_callable=AsyncMock,
    )
    async def test_revise_after_revise_still_accepts_approve(
        self,
        mock_get_state: AsyncMock,
        mock_resume: AsyncMock,
        client: AsyncClient,
    ) -> None:
        editor = await create_user("revise-then-approve@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        prior_state = {
            "project_id": project_id,
            "current_phase": PHASE_OUTLINE,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "outline": [
                {"slide_index": 1, "title": "Intro"},
                {"slide_index": 2, "title": "Body"},
            ],
            "phase_feedback": {PHASE_OUTLINE: ["Merge slides 3 and 4"]},
            "revision_count": {PHASE_OUTLINE: 1},
        }
        advanced_state = {
            **prior_state,
            "current_phase": PHASE_CONTENT,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "slide_drafts": [{"draft_text": "Merged intro"}],
        }
        mock_get_state.return_value = prior_state
        mock_resume.return_value = advanced_state
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": version},
            headers=auth_header(editor),
        )

        assert response.status_code == 202
        await drain_background_tasks()
        mock_resume.assert_awaited_once()
