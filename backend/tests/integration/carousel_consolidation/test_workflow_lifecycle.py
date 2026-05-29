"""Carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_CONTENT,
    PHASE_FINAL_REVIEW,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    drain_background_tasks,
    get_lock_version,
    seed_workflow_phase,
    wait_for_workflow_state,
)


class TestEditorialWorkflowLifecycle:
    """Scenarios: start, approve, revise, persona gate, checkpoint recovery."""

    @pytest.mark.asyncio
    @patch(
        "rag_backend.agents.carousel_editorial_orchestrator.CarouselEditorialOrchestrator.synthesize_research",
        new_callable=AsyncMock,
    )
    async def test_start_workflow_pauses_at_research_gate(
        self,
        mock_research: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Start workflow and pause at first human gate."""
        mock_research.return_value = [
            {"title": "Primary source", "summary": "Key finding for review"},
        ]
        editor = await create_user("start-gate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/start",
            json={
                "topic": "AI Safety",
                "audience": "Engineers",
                "brief": "Explain guardrails",
                "sources": [],
            },
            headers=auth_header(editor),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["current_phase"] == PHASE_RESEARCH
        assert payload["phase_status"] == PHASE_STATUS_AWAITING_HUMAN
        assert payload["research_findings"]

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.phase_artifact_runner.generate_outline",
        new_callable=AsyncMock,
    )
    async def test_approve_research_advances_to_outline_gate(
        self,
        mock_outline: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Approve research advances to outline generation inside graph."""
        mock_outline.return_value = [
            {"slide_index": 1, "title": "Intro", "key_points": ["Hook"]},
        ]
        editor = await create_user("approve-research@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "research_findings": [{"title": "Finding", "summary": "Detail"}],
                "research_approved": False,
            },
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": version},
            headers=auth_header(editor),
        )

        assert response.status_code == 202
        accepted = response.json()
        assert accepted["accepted"] is True
        assert accepted["phase_status"] == PHASE_STATUS_IN_PROGRESS
        await drain_background_tasks()
        payload = await wait_for_workflow_state(
            client,
            project_id,
            auth_header(editor),
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )
        assert payload["outline"]
        mock_outline.assert_called()

    @pytest.mark.asyncio
    async def test_revise_research_stays_in_research_phase(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Revise research loops in-graph without stuck END checkpoint."""
        editor = await create_user("revise-research@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "research_findings": [{"title": "Finding", "summary": "Detail"}],
            },
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "feedback": "Include more recent sources from primary URLs",
                "expected_version": version,
            },
            headers=auth_header(editor),
        )

        assert response.status_code == 202
        await drain_background_tasks()
        payload = await wait_for_workflow_state(
            client,
            project_id,
            auth_header(editor),
            phase=PHASE_RESEARCH,
        )
        assert payload["current_phase"] == PHASE_RESEARCH
        assert payload["phase_status"] in {
            PHASE_STATUS_AWAITING_HUMAN,
            PHASE_STATUS_IN_PROGRESS,
        }

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator.get_state",
        new_callable=AsyncMock,
    )
    async def test_content_approve_blocked_when_persona_below_threshold(
        self,
        mock_get_state: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Content approve blocked when persona score below threshold."""
        editor = await create_user("persona-gate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        mock_get_state.return_value = {
            "project_id": project_id,
            "current_phase": PHASE_CONTENT,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "persona_scores": {"default": {"overall": 65}},
            "slide_drafts": [{"draft_text": "Slide body"}],
        }
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": version},
            headers=auth_header(editor),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == ERR_PERSONA_SCORE_TOO_LOW

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator.get_state",
        new_callable=AsyncMock,
    )
    async def test_revision_cap_triggers_escalation(
        self,
        mock_get_state: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Revision cap triggers escalation."""
        editor = await create_user("revision-cap@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        mock_get_state.return_value = {
            "project_id": project_id,
            "current_phase": PHASE_CONTENT,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "revision_count": {PHASE_CONTENT: 5},
            "slide_drafts": [{"draft_text": "Slide body"}],
        }
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "feedback": "Try again",
                "expected_version": version,
            },
            headers=auth_header(editor),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == ERR_REVISION_CAP_EXCEEDED

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator.resume",
        new_callable=AsyncMock,
    )
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator.get_state",
        new_callable=AsyncMock,
    )
    async def test_final_review_approve_does_not_set_is_public(
        self,
        mock_get_state: AsyncMock,
        mock_resume: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Final review approve does not set is_public."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        editor = await create_user("final-approve@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        approved_state = {
            "project_id": project_id,
            "current_phase": PHASE_FINAL_REVIEW,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            "quality_passed": True,
        }
        mock_get_state.return_value = {
            "project_id": project_id,
            "current_phase": PHASE_FINAL_REVIEW,
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "quality_passed": False,
            "outline": [{"title": "Intro"}],
            "slide_drafts": [{"draft_text": "Body"}],
            "research_findings": [{"title": "Finding"}],
        }

        async def get_state_side_effect(project_id_arg: str) -> dict[str, object]:
            if mock_resume.called:
                return approved_state
            return mock_get_state.return_value

        mock_get_state.side_effect = get_state_side_effect
        mock_resume.return_value = approved_state
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": version},
            headers=auth_header(editor),
        )

        assert response.status_code == 202
        await drain_background_tasks()
        mock_resume.assert_awaited_once()

        session_maker = get_session_maker()
        async with session_maker() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            assert model.is_public is False
            assert model.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH

    @pytest.mark.asyncio
    async def test_caption_endpoint_returns_stored_caption_without_pipeline(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Caption endpoint does not run full legacy pipeline."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        editor = await create_user("caption@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        session_maker = get_session_maker()
        async with session_maker() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            model.caption = "Stored workflow caption"
            await session.commit()

        response = await client.post(
            f"/api/carousels/{project_id}/caption",
            headers=auth_header(editor),
        )

        assert response.status_code == 200
        assert response.json()["caption"] == "Stored workflow caption"

    @pytest.mark.asyncio
    async def test_workflow_checkpoint_survives_engine_reinit(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Resume workflow after server restart."""
        from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine

        editor = await create_user("recovery@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_CONTENT,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "slide_drafts": [{"draft_text": "Persisted draft"}],
            },
        )

        checkpointer = client.app.state.carousel_checkpointer  # type: ignore[attr-defined]
        reloaded_engine = CarouselWorkflowEngine(checkpointer=checkpointer)
        snapshot = await reloaded_engine._app.aget_state(
            reloaded_engine._run_config(project_id)
        )
        assert snapshot is not None
        values = snapshot.values
        assert isinstance(values, dict)
        assert values["current_phase"] == PHASE_CONTENT
        assert values["phase_status"] == PHASE_STATUS_AWAITING_HUMAN
        assert values["slide_drafts"]
