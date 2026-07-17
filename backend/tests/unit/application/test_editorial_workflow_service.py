"""Unit tests for EditorialWorkflowService business rules."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
    ResumeWorkflowInput,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_CONTENT,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


@pytest.fixture
def service() -> EditorialWorkflowService:
    llm = MagicMock()
    return EditorialWorkflowService(EditorialWorkflowConfig(llm=llm))


class TestEditorialWorkflowServiceInit:
    """Scenario: EditorialWorkflowService __init__ with different parameters."""

    def test_init_with_llm_only(self) -> None:
        """Given only llm, when creating service, then orchestrator is created."""
        llm = MagicMock()
        service = EditorialWorkflowService(EditorialWorkflowConfig(llm=llm))
        assert service._llm is llm
        assert service._orchestrator is not None

    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator"
    )
    def test_init_passes_llm_to_orchestrator(
        self, mock_orchestrator: MagicMock
    ) -> None:
        """Given llm, when creating service, then orchestrator receives llm."""
        llm = MagicMock()
        EditorialWorkflowService(EditorialWorkflowConfig(llm=llm))
        assert mock_orchestrator.call_args.kwargs["llm"] is llm

    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator"
    )
    def test_init_passes_checkpointer_to_orchestrator(
        self, mock_orchestrator: MagicMock
    ) -> None:
        """Given checkpointer, when creating service, then orchestrator receives checkpointer."""
        llm = MagicMock()
        checkpointer = MagicMock()
        EditorialWorkflowService(
            EditorialWorkflowConfig(llm=llm, checkpointer=checkpointer),
        )
        assert mock_orchestrator.call_args.kwargs["checkpointer"] is checkpointer

    def test_init_with_event_service(self) -> None:
        """Given event_service, when creating service, then events is set."""
        llm = MagicMock()
        event_service = MagicMock()
        service = EditorialWorkflowService(
            EditorialWorkflowConfig(llm=llm, event_service=event_service),
        )
        assert service._events is event_service

    def test_init_with_notification_service(self) -> None:
        """Given notification_service, when creating service, then notifications is set."""
        llm = MagicMock()
        notification_service = MagicMock()
        service = EditorialWorkflowService(
            EditorialWorkflowConfig(llm=llm, notification_service=notification_service),
        )
        assert service._notifications is notification_service

    def test_init_with_image_registry(self) -> None:
        """Given image_registry, when creating service, then orchestrator has registry."""
        llm = MagicMock()
        image_registry = MagicMock()
        service = EditorialWorkflowService(
            EditorialWorkflowConfig(llm=llm, image_registry=image_registry),
        )
        assert service._orchestrator is not None

    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.CarouselEditorialOrchestrator"
    )
    def test_init_passes_image_registry_to_orchestrator(
        self, mock_orchestrator: MagicMock
    ) -> None:
        """Given image_registry, when creating service, then orchestrator receives image_registry."""
        llm = MagicMock()
        image_registry = MagicMock()
        EditorialWorkflowService(
            EditorialWorkflowConfig(llm=llm, image_registry=image_registry),
        )
        assert mock_orchestrator.call_args.kwargs["image_registry"] is image_registry


class TestEditorialWorkflowServiceSyncProjectPhase:
    """Scenario: _sync_project_phase keeps project row in sync with workflow state."""

    @pytest.mark.asyncio
    async def test_skips_when_db_is_none(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given db is None, when syncing, then returns early."""
        state: dict[str, object] = {"current_phase": "research"}
        result = await service._sync_project_phase(None, "project-1", state)
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_when_project_not_found(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given project not found, when syncing, then returns early."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        state: dict[str, object] = {"current_phase": "research"}
        result = await service._sync_project_phase(db, "project-1", state)
        assert result is None
        db.get.assert_awaited_once_with(CarouselProjectModel, "project-1")

    @pytest.mark.asyncio
    async def test_updates_phase_and_status(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given valid project, when syncing, then phase and status are updated."""
        db = AsyncMock()
        project = MagicMock()
        project.current_phase = "outline"
        project.phase_status = "awaiting_human"
        project.status = "draft"
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": "in_progress",
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.current_phase == "research"
        assert project.phase_status == "in_progress"
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sets_failed_status(self, service: EditorialWorkflowService) -> None:
        """Given phase_status is failed, when syncing, then project status is failed."""
        db = AsyncMock()
        project = MagicMock()
        project.status = CarouselStatus.DRAFTING.value
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": PHASE_STATUS_FAILED,
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.status == CarouselStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_updates_workflow_status(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given workflow_status in state, when syncing, then workflow_status is updated."""
        db = AsyncMock()
        project = MagicMock()
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": "in_progress",
            "workflow_status": "approved",
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.workflow_status == "approved"

    @pytest.mark.asyncio
    async def test_skips_workflow_status_when_none(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given workflow_status is None, when syncing, then workflow_status is not updated."""
        db = AsyncMock()
        project = MagicMock()
        project.workflow_status = "existing"
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": "in_progress",
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.workflow_status == "existing"

    @pytest.mark.asyncio
    async def test_does_not_write_caption_to_embedded_column(
        self, service: EditorialWorkflowService
    ) -> None:
        """AE-0204: the checkpoint sync no longer writes the embedded caption column.

        Caption has a canonical home (``blog_posts.distribution``); the checkpoint
        sync is decoupled so a resumed checkpoint cannot resurrect an embedded-column
        write. The embedded ``project.caption`` is left UNCHANGED by the sync.
        """
        db = AsyncMock()
        project = MagicMock()
        project.caption = "pre-existing"
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": "in_progress",
            "caption": "Test caption",
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.caption == "pre-existing"

    @pytest.mark.asyncio
    async def test_updates_blog_markdown(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given blog_markdown in state, when syncing, then blog_markdown is updated.

        ``blog_markdown`` remains synced (AE-0163's domain) — only the AE-0204
        distribution fields were removed from the checkpoint sync.
        """
        db = AsyncMock()
        project = MagicMock()
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": "in_progress",
            "blog_markdown": "# Test",
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.blog_markdown == "# Test"

    @pytest.mark.asyncio
    async def test_does_not_write_linkedin_posts_to_embedded_columns(
        self, service: EditorialWorkflowService
    ) -> None:
        """AE-0204: the checkpoint sync no longer writes the embedded LinkedIn columns.

        LinkedIn posts have a canonical home (``blog_posts.distribution``); the
        decoupled sync leaves the embedded columns UNCHANGED.
        """
        db = AsyncMock()
        project = MagicMock()
        project.linkedin_post_pt = "pre-existing-pt"
        project.linkedin_post_en = "pre-existing-en"
        db.get = AsyncMock(return_value=project)
        state: dict[str, object] = {
            "current_phase": "research",
            "phase_status": "in_progress",
            "linkedin_post_pt": "PT post",
            "linkedin_post_en": "EN post",
        }
        await service._sync_project_phase(db, "project-1", state)
        assert project.linkedin_post_pt == "pre-existing-pt"
        assert project.linkedin_post_en == "pre-existing-en"


class TestEditorialWorkflowServiceGetState:
    """Scenario: get_workflow_state with different branches."""

    @pytest.mark.asyncio
    async def test_returns_none_when_orchestrator_returns_none(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given orchestrator returns None, when getting state, then returns None."""
        service._orchestrator.get_state = AsyncMock(return_value=None)
        result = await service.get_workflow_state("project-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_phase_is_empty(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given phase is empty string, when getting state, then returns None."""
        service._orchestrator.get_state = AsyncMock(
            return_value={"current_phase": "", "phase_status": "awaiting_human"}
        )
        result = await service.get_workflow_state("project-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_phase_is_whitespace(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given phase is whitespace, when getting state, then returns None."""
        service._orchestrator.get_state = AsyncMock(
            return_value={"current_phase": "  ", "phase_status": "awaiting_human"}
        )
        result = await service.get_workflow_state("project-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_db_merge_when_db_is_none(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given db is None, when getting state, then returns checkpoint status."""
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": "research",
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        result = await service.get_workflow_state("project-1", db=None)
        assert result is not None
        assert result["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

    @pytest.mark.asyncio
    async def test_merges_db_in_progress_status(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given DB says in_progress and checkpoint says awaiting_human,
        when getting state, then returns in_progress."""
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        db = AsyncMock()
        project = MagicMock()
        project.phase_status = PHASE_STATUS_IN_PROGRESS
        db.get = AsyncMock(return_value=project)
        result = await service.get_workflow_state("project-1", db=db)
        assert result is not None
        assert result["phase_status"] == PHASE_STATUS_IN_PROGRESS

    @pytest.mark.asyncio
    async def test_returns_checkpoint_when_db_agrees(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given both DB and checkpoint say awaiting_human,
        when getting state, then returns awaiting_human."""
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        db = AsyncMock()
        project = MagicMock()
        project.phase_status = PHASE_STATUS_AWAITING_HUMAN
        db.get = AsyncMock(return_value=project)
        result = await service.get_workflow_state("project-1", db=db)
        assert result is not None
        assert result["phase_status"] == PHASE_STATUS_AWAITING_HUMAN


class TestEditorialWorkflowServiceMarkResumeInProgress:
    """Scenario: mark_resume_in_progress with different states."""

    @pytest.mark.asyncio
    async def test_returns_phase_when_prior_is_none(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given prior is None, when marking in_progress, then returns empty string."""
        service._orchestrator.get_state = AsyncMock(return_value=None)
        service._sync_project_phase = AsyncMock()  # type: ignore[method-assign]
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_phase_change",
        ):
            phase = await service.mark_resume_in_progress("project-1", db=None)
        assert phase == ""

    @pytest.mark.asyncio
    async def test_calls_sync_project_phase_with_db(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given db is provided, when marking in_progress, then _sync_project_phase is called."""
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        service._sync_project_phase = AsyncMock()  # type: ignore[method-assign]
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_phase_change",
        ):
            phase = await service.mark_resume_in_progress("project-1", db=AsyncMock())
        assert phase == PHASE_RESEARCH
        service._sync_project_phase.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_calls_sync_project_phase_with_correct_state(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given prior state, when marking in_progress, then _sync_project_phase receives correct state."""
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        service._sync_project_phase = AsyncMock()  # type: ignore[method-assign]
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_phase_change",
        ):
            await service.mark_resume_in_progress("project-1", db=None)
        call_args = service._sync_project_phase.call_args
        assert call_args[0][1] == "project-1"
        state = call_args[0][2]
        assert state["phase_status"] == PHASE_STATUS_IN_PROGRESS
        assert state["current_phase"] == PHASE_RESEARCH


class TestEditorialWorkflowServicePublishResumeErrorEvent:
    """Scenario: publish_resume_error_event with different parameters."""

    @pytest.mark.asyncio
    async def test_publishes_error_with_phase(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given valid project, when publishing error, then phase is included."""
        service._orchestrator.get_state = AsyncMock(
            return_value={"current_phase": PHASE_RESEARCH}
        )
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_error",
        ) as mock_publish:
            await service.publish_resume_error_event(
                "project-1",
                message="Test error",
                recoverable=True,
            )
        mock_publish.assert_awaited_once()
        call_args = mock_publish.call_args
        params = call_args[0][0]
        assert params.project_id == "project-1"
        assert params.phase == PHASE_RESEARCH
        assert call_args[0][1] == "Test error"
        assert call_args.kwargs["recoverable"] is True

    @pytest.mark.asyncio
    async def test_publishes_error_with_empty_phase(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given prior is None, when publishing error, then empty phase is used."""
        service._orchestrator.get_state = AsyncMock(return_value=None)
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_error",
        ) as mock_publish:
            await service.publish_resume_error_event(
                "project-1",
                message="Test error",
                recoverable=False,
            )
        mock_publish.assert_awaited_once()
        call_args = mock_publish.call_args
        assert call_args[0][0].phase == ""
        assert call_args.kwargs["recoverable"] is False

    @pytest.mark.asyncio
    async def test_publishes_error_with_recoverable_true(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given recoverable=True, when publishing error, then recoverable is passed."""
        service._orchestrator.get_state = AsyncMock(
            return_value={"current_phase": PHASE_RESEARCH}
        )
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_error",
        ) as mock_publish:
            await service.publish_resume_error_event(
                "project-1",
                message="Test error",
                recoverable=True,
            )
        assert mock_publish.call_args.kwargs["recoverable"] is True

    @pytest.mark.asyncio
    async def test_publishes_error_with_recoverable_false(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given recoverable=False, when publishing error, then recoverable is passed."""
        service._orchestrator.get_state = AsyncMock(
            return_value={"current_phase": PHASE_RESEARCH}
        )
        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_error",
        ) as mock_publish:
            await service.publish_resume_error_event(
                "project-1",
                message="Test error",
                recoverable=False,
            )
        assert mock_publish.call_args.kwargs["recoverable"] is False


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
                ResumeWorkflowInput(
                    project_id=project_id,
                    action=REVIEW_ACTION_APPROVE,
                    reviewer_id="reviewer-1",
                ),
            )

    @pytest.mark.asyncio
    async def test_rejects_content_approve_when_presentation_validation_blocks(
        self, service: EditorialWorkflowService
    ) -> None:
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_CONTENT,
                "presentation_validation": {
                    "validation_status": "invalid",
                    "validated_at": "2026-06-09T00:00:00+00:00",
                    "blocking": True,
                    "violations": [
                        {
                            "code": "visible_emoji_forbidden",
                            "message": "Visible text must not contain decorative emoji",
                            "slide_index": 1,
                            "locale": "pt",
                            "field": "heading",
                        }
                    ],
                },
            }
        )

        with pytest.raises(ValueError, match=ERR_PRESENTATION_VALIDATION_BLOCKED):
            await service.resume_workflow(
                ResumeWorkflowInput(
                    project_id=str(uuid4()),
                    action=REVIEW_ACTION_APPROVE,
                    reviewer_id="reviewer-1",
                ),
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
                ResumeWorkflowInput(
                    project_id=project_id,
                    action=REVIEW_ACTION_REVISE,
                    reviewer_id="reviewer-1",
                    feedback="Needs more detail",
                    db=MagicMock(),
                    project_title="Test carousel",
                ),
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
            ResumeWorkflowInput(
                project_id=project_id,
                action=REVIEW_ACTION_APPROVE,
                reviewer_id="reviewer-1",
            ),
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


class TestEditorialWorkflowServiceGetStateBlank:
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


class TestMarkResumeInProgress:
    """Scenario: mark_resume_in_progress does NOT clear LangGraph interrupts.

    When mark_resume_in_progress is called the system SHALL NOT call
    update_state on the orchestator (which would patch the checkpoint and
    clear pending interrupts). Only the DB row and SSE publish are updated.
    (see .agent/tasks/AE-0025-workflow-resume-interrupt-corruption.md)
    """

    @pytest.mark.asyncio
    async def test_does_not_call_update_state_on_orchestrator(
        self, service: EditorialWorkflowService
    ) -> None:
        """Given a workflow paused at research gate, when mark_resume_in_progress,
        then update_state is NOT called (interrupt preserved)."""
        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": "awaiting_human",
            }
        )
        service._orchestrator.update_state = AsyncMock()
        service._sync_project_phase = AsyncMock()  # type: ignore[method-assign]

        with patch(
            "rag_backend.application.services.carousel.editorial_workflow_support.publish_workflow_phase_change",
        ):
            phase = await service.mark_resume_in_progress(project_id, db=None)

        assert phase == PHASE_RESEARCH
        service._orchestrator.update_state.assert_not_called()


class TestGetWorkflowStateDBMerge:
    """AE-0026: get_workflow_state merges DB phase_status when DB says
    in_progress but checkpoint says awaiting_human."""

    @pytest.mark.asyncio
    async def test_db_in_progress_overrides_checkpoint_awaiting_human(
        self, service: EditorialWorkflowService
    ) -> None:
        """When DB says in_progress and checkpoint says awaiting_human,
        get_workflow_state SHALL return in_progress."""
        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        mock_db = AsyncMock()
        mock_project = MagicMock()
        mock_project.phase_status = PHASE_STATUS_IN_PROGRESS
        mock_project.id = project_id
        mock_db.get = AsyncMock(return_value=mock_project)

        state = await service.get_workflow_state(project_id, db=mock_db)

        assert state is not None
        assert state["phase_status"] == PHASE_STATUS_IN_PROGRESS

    @pytest.mark.asyncio
    async def test_db_awaiting_human_preserved_when_checkpoint_agrees(
        self, service: EditorialWorkflowService
    ) -> None:
        """When both DB and checkpoint say awaiting_human,
        get_workflow_state SHALL return awaiting_human."""
        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        mock_db = AsyncMock()
        mock_project = MagicMock()
        mock_project.phase_status = PHASE_STATUS_AWAITING_HUMAN
        mock_project.id = project_id
        mock_db.get = AsyncMock(return_value=mock_project)

        state = await service.get_workflow_state(project_id, db=mock_db)

        assert state is not None
        assert state["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

    @pytest.mark.asyncio
    async def test_no_db_session_returns_checkpoint_status(
        self, service: EditorialWorkflowService
    ) -> None:
        """When no DB session is provided, get_workflow_state SHALL return
        the checkpoint phase_status without DB merge."""
        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )

        state = await service.get_workflow_state(project_id, db=None)

        assert state is not None
        assert state["phase_status"] == PHASE_STATUS_AWAITING_HUMAN


class TestEditorialWorkflowServiceLangfuseTraceMetadata:
    """AE-0050: Langfuse trace metadata is preserved after the wave-3/4 refactors.

    Scenario (see Gherkin "Langfuse Trace Preservation"): a refactored editorial
    workflow operation with a Langfuse callback must still propagate the required
    trace metadata fields. start_workflow wires two Langfuse surfaces:
      - create_workflow_trace -> project_id, user_id, content_type, content metadata
      - propagate_attributes  -> project_id, phase
    The agent_name field is supplied at the agent/orchestrator layer (rag_agent /
    alter_ego_agent), outside this service, so it is asserted on the trace name
    instead of as a metadata key here.
    """

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.publish_workflow_sse_updates",
        new_callable=AsyncMock,
    )
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.emit_phase_event",
        new_callable=AsyncMock,
    )
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.propagate_attributes"
    )
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.create_workflow_trace",
        return_value=None,
    )
    async def test_start_workflow_propagates_langfuse_metadata(
        self,
        mock_create_trace: MagicMock,
        mock_propagate: MagicMock,
        _emit_phase: AsyncMock,
        _publish_sse: AsyncMock,
        service: EditorialWorkflowService,
    ) -> None:
        """Given a Langfuse callback, when start_workflow runs with project_id,
        phase, user_id and content_type, then the trace and span carry them all."""
        # propagate_attributes is a context manager; make the patch behave like one.
        mock_propagate.return_value.__enter__ = MagicMock(return_value=None)
        mock_propagate.return_value.__exit__ = MagicMock(return_value=False)

        project_id = str(uuid4())
        service._orchestrator.get_state = AsyncMock(return_value=None)
        service._orchestrator.synthesize_research = AsyncMock(return_value={})
        service._orchestrator.start = AsyncMock(
            return_value={
                "current_phase": PHASE_RESEARCH,
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        service._events = None

        await service.start_workflow(
            project_id=project_id,
            workflow_input=EditorialWorkflowStartInput(
                topic="AI",
                audience="devs",
                brief="brief",
                sources=[],
                user_id="pedro-user-id",
            ),
        )

        # create_workflow_trace metadata: project_id, user_id, content_type.
        trace_config = mock_create_trace.call_args.kwargs["config"]
        assert str(trace_config["project_id"]) == project_id
        assert trace_config["user_id"] == "pedro-user-id"
        assert trace_config["content_type"] == CONTENT_TYPE_CAROUSEL

        # propagate_attributes metadata: project_id + phase.
        span_metadata = mock_propagate.call_args.kwargs["metadata"]
        assert span_metadata["project_id"] == project_id
        assert span_metadata["phase"] == PHASE_RESEARCH


class TestMarkResumeInProgressPublishLock:
    """AE-0288: a send-back from an approved carousel drops the DB publish lock
    synchronously so a concurrent publish cannot ship stale content mid-regen.
    """

    _PUBLISH_PHASE_CHANGE = (
        "rag_backend.application.services.carousel"
        ".editorial_workflow_support.publish_workflow_phase_change"
    )

    @pytest.mark.asyncio
    async def test_clears_publish_lock_when_prior_approved_for_publish(
        self, service: EditorialWorkflowService
    ) -> None:
        from rag_backend.domain.constants.carousel_workflow import (
            CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
            WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
        )

        prior = AsyncMock(
            return_value={
                "current_phase": "final_review",
                "workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            }
        )
        sync = AsyncMock()
        with (
            patch.object(service, "get_workflow_state", prior),
            patch.object(service, "_sync_project_phase", sync),
            patch(self._PUBLISH_PHASE_CHANGE, new=AsyncMock()),
        ):
            await service.mark_resume_in_progress("project-1", AsyncMock())

        synced_state = sync.await_args.args[2]
        assert (
            synced_state["workflow_status"] == CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
        )

    @pytest.mark.asyncio
    async def test_keeps_workflow_status_when_not_approved(
        self, service: EditorialWorkflowService
    ) -> None:
        from rag_backend.domain.constants.carousel_workflow import (
            WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
        )

        prior = AsyncMock(
            return_value={"current_phase": "content", "workflow_status": "draft"}
        )
        sync = AsyncMock()
        with (
            patch.object(service, "get_workflow_state", prior),
            patch.object(service, "_sync_project_phase", sync),
            patch(self._PUBLISH_PHASE_CHANGE, new=AsyncMock()),
        ):
            await service.mark_resume_in_progress("project-1", AsyncMock())

        synced_state = sync.await_args.args[2]
        assert synced_state["workflow_status"] != WORKFLOW_STATUS_APPROVED_FOR_PUBLISH


class TestStartWorkflowResearchEnrichment:
    """AE-0317 scenarios (tests/features/research_enrichment.feature)."""

    def test_init_threads_research_tool(self) -> None:
        """Scenario: URL source is navigated (wiring half)."""
        research_tool = MagicMock()
        service = EditorialWorkflowService(
            EditorialWorkflowConfig(llm=MagicMock(), research_tool=research_tool)
        )
        assert service._research_tool is research_tool

    def test_init_defaults_research_tool_to_none(self) -> None:
        """Scenario: Enrichment disabled restores legacy behavior (wiring half)."""
        service = EditorialWorkflowService(EditorialWorkflowConfig(llm=MagicMock()))
        assert service._research_tool is None

    @pytest.mark.asyncio
    async def test_start_workflow_synthesizes_and_briefs_enriched_sources(
        self,
    ) -> None:
        """Scenario: URL source is navigated and its content informs research."""
        research_tool = MagicMock()
        service = EditorialWorkflowService(
            EditorialWorkflowConfig(llm=MagicMock(), research_tool=research_tool)
        )
        raw_sources = [
            {"title": "u", "content": "https://example.com/a", "source_type": "url"}
        ]
        enriched_sources = [
            {"title": "u", "content": "scraped body", "source_type": "url"},
            {
                "title": "hit",
                "content": "snippet",
                "source_type": "web_search",
                "url": "https://hit.example.com",
            },
        ]
        started_state = {
            "current_phase": PHASE_RESEARCH,
            "phase_status": PHASE_STATUS_IN_PROGRESS,
        }
        orchestrator = MagicMock()
        orchestrator.get_state = AsyncMock(side_effect=[None, None])
        orchestrator.enrich_research_sources = AsyncMock(return_value=enriched_sources)
        orchestrator.synthesize_research = AsyncMock(return_value=[])
        orchestrator.start = AsyncMock(return_value=started_state)
        service._orchestrator = orchestrator

        state = await service.start_workflow(
            str(uuid4()),
            EditorialWorkflowStartInput(
                topic="topic",
                audience="aud",
                brief="brief",
                sources=raw_sources,
            ),
        )

        assert state == started_state
        enrich_call = orchestrator.enrich_research_sources.await_args
        assert enrich_call.args[0] == raw_sources
        assert enrich_call.args[1].topic == "topic"
        assert enrich_call.args[1].research_tool is research_tool
        orchestrator.synthesize_research.assert_awaited_once_with(enriched_sources)
        initial_brief = orchestrator.start.await_args.args[1]
        assert initial_brief["sources"] == enriched_sources
