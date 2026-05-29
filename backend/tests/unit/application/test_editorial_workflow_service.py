"""Unit tests for EditorialWorkflowService business rules."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_CONTENT,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE


@pytest.fixture
def service() -> EditorialWorkflowService:
    llm = MagicMock()
    return EditorialWorkflowService(llm=llm)


class TestEditorialWorkflowServiceResume:
    """Scenario: Content approve blocked when persona score below threshold."""

    @pytest.mark.asyncio
    async def test_rejects_content_approve_when_persona_score_low(
        self, service: EditorialWorkflowService
    ) -> None:
        project_id = str(uuid4())
        low_score = float(VOICE_MATCH_MIN_SCORE) - 1
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_CONTENT,
                "persona_scores": {"default": {"overall": low_score}},
                "revision_count": {},
            }
        )

        with pytest.raises(ValueError, match=ERR_PERSONA_SCORE_TOO_LOW):
            await service.resume_workflow(
                project_id=project_id,
                action=REVIEW_ACTION_APPROVE,
                reviewer_id="reviewer-1",
            )

    @pytest.mark.asyncio
    async def test_rejects_revise_when_revision_cap_exceeded(
        self, service: EditorialWorkflowService
    ) -> None:
        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_CONTENT,
                "revision_count": {PHASE_CONTENT: 5},
            }
        )
        service._notifications = MagicMock()
        service._notifications.create_revision_cap_escalation = AsyncMock()

        with pytest.raises(ValueError, match=ERR_REVISION_CAP_EXCEEDED):
            await service.resume_workflow(
                project_id=project_id,
                action=REVIEW_ACTION_REVISE,
                reviewer_id="reviewer-1",
                feedback="Needs more detail",
                db=MagicMock(),
                project_title="Test carousel",
            )

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.emit_review_event",
        new_callable=AsyncMock,
    )
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.create_workflow_trace",
        return_value=None,
    )
    async def test_resume_delegates_to_orchestrator_on_valid_approve(
        self,
        _trace: MagicMock,
        _emit_review: AsyncMock,
        service: EditorialWorkflowService,
    ) -> None:
        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(
            side_effect=[
                {"current_phase": "research", "revision_count": {}},
                {"current_phase": "outline", "phase_status": "awaiting_human"},
            ]
        )
        service._orchestrator.resume = AsyncMock(
            return_value={"current_phase": "outline", "phase_status": "awaiting_human"}
        )
        service._events = None

        state = await service.resume_workflow(
            project_id=project_id,
            action=REVIEW_ACTION_APPROVE,
            reviewer_id="reviewer-1",
        )

        assert state["current_phase"] == "outline"
        service._orchestrator.resume.assert_awaited_once()
        resume_kwargs = service._orchestrator.resume.await_args.kwargs
        assert resume_kwargs["db"] is None
        assert resume_kwargs["workflow_input"] is not None


class TestEditorialWorkflowServiceStart:
    """Scenario: Start workflow returns existing state when already active."""

    @pytest.mark.asyncio
    async def test_start_returns_existing_state_without_restart(
        self, service: EditorialWorkflowService
    ) -> None:
        project_id = str(uuid4())
        existing_state = {"current_phase": "research", "phase_status": "awaiting_human"}
        service._orchestrator.get_state = AsyncMock(return_value=existing_state)
        service._orchestrator.synthesize_research = AsyncMock()

        state = await service.start_workflow(
            project_id=project_id,
            workflow_input=MagicMock(user_id="user-1", reviewer_id=None),
        )

        assert state == existing_state
        service._orchestrator.synthesize_research.assert_not_called()


class TestEditorialWorkflowServiceGetState:
    """Scenario: get_workflow_state ignores empty phase checkpoints."""

    @pytest.mark.asyncio
    async def test_returns_none_when_phase_blank(
        self, service: EditorialWorkflowService
    ) -> None:
        service._orchestrator.get_state = AsyncMock(
            return_value={"current_phase": "  ", "phase_status": "pending"}
        )

        state = await service.get_workflow_state(str(uuid4()))

        assert state is None
