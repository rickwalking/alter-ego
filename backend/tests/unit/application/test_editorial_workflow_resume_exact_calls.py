"""Exact collaborator calls made by EditorialWorkflowService.resume_workflow.

Feature: Carousel editorial workflow safety net (resume after human review)
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.edited_slide_persist import (
    EditedSlidePersistCommand,
)
from rag_backend.application.services.carousel.editorial_workflow_events import (
    ReviewEventEmitRequest,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    FeedbackCorrectionContext,
    RevisionCapValidationContext,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
    ResumeWorkflowInput,
    ReviewEventEmitContext,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_IMAGES,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_KEY,
    WORKFLOW_TRACE_PHASE_REVIEW,
)
from rag_backend.domain.models.carousels import ReviewEventParams

_SERVICE = "rag_backend.application.services.carousel.editorial_workflow_service"
_FINALIZE = (
    "rag_backend.application.services.carousel.editorial_finalize."
    "finalize_carousel_after_images_approval"
)
_PROJECT_ID = "proj-resume-1"
_REVIEWER_ID = "reviewer-77"
_PROJECT_TITLE = "Guardrails carousel"
_FEEDBACK = "warmer light please"
_NEXT_PHASE = "design"
_ACTION_KEY = "action"
_REVIEWER_KEY = "reviewer_id"
_FEEDBACK_KEY = "feedback"
_CURRENT_PHASE_KEY = "current_phase"
_PHASE_STATUS_KEY = "phase_status"
_APPEND_VISUAL_FEEDBACK = "_append_image_visual_feedback"


@dataclass
class _Harness:
    """The service under test plus every collaborator double it calls."""

    service: EditorialWorkflowService
    orchestrator: MagicMock
    events: MagicMock
    notifications: MagicMock
    validate_cap: AsyncMock
    prepare: AsyncMock
    record_review: MagicMock
    record_correction: AsyncMock
    persist_edits: AsyncMock
    emit_review: AsyncMock
    publish_sse: AsyncMock
    finalize: AsyncMock
    append_visual: AsyncMock
    persona: MagicMock
    db: AsyncMock
    structured: dict[str, object]


@pytest.fixture
def harness() -> Iterator[_Harness]:
    events = MagicMock()
    notifications = MagicMock()
    service = EditorialWorkflowService(
        EditorialWorkflowConfig(
            llm=MagicMock(),
            event_service=events,
            notification_service=notifications,
        )
    )
    orchestrator = MagicMock()
    orchestrator.resume = AsyncMock()
    service._orchestrator = orchestrator
    with (
        patch.object(
            service, _APPEND_VISUAL_FEEDBACK, new=AsyncMock()
        ) as append_visual,
        patch(f"{_SERVICE}.validate_revision_cap", new=AsyncMock()) as validate_cap,
        patch(f"{_SERVICE}.prepare_resume_workflow", new=AsyncMock()) as prepare,
        patch(f"{_SERVICE}.record_human_review") as record_review,
        patch(
            f"{_SERVICE}.record_feedback_correction", new=AsyncMock()
        ) as record_correction,
        patch(f"{_SERVICE}.persist_edited_slide_copy", new=AsyncMock()) as persist,
        patch(f"{_SERVICE}.emit_review_event", new=AsyncMock()) as emit_review,
        patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()) as sse,
        patch(f"{_SERVICE}.CarouselProjectWriteOwner") as owner,
        patch(_FINALIZE, new=AsyncMock()) as finalize,
    ):
        owner.return_value.sync_phase = AsyncMock()
        owner.return_value.commit = AsyncMock()
        yield _Harness(
            service=service,
            orchestrator=orchestrator,
            events=events,
            notifications=notifications,
            validate_cap=validate_cap,
            prepare=prepare,
            record_review=record_review,
            record_correction=record_correction,
            persist_edits=persist,
            emit_review=emit_review,
            publish_sse=sse,
            finalize=finalize,
            append_visual=append_visual,
            persona=MagicMock(),
            db=AsyncMock(),
            structured={"slides": [{"slide_index": 1}]},
        )


def _with_states(
    harness: _Harness,
    prior: Mapping[str, object] | None,
    result: Mapping[str, object],
) -> None:
    harness.orchestrator.get_state = AsyncMock(side_effect=[prior, result])
    harness.orchestrator.resume.return_value = result


def _input(
    harness: _Harness, action: str, feedback: str | None = _FEEDBACK
) -> ResumeWorkflowInput:
    return ResumeWorkflowInput(
        project_id=_PROJECT_ID,
        action=action,
        reviewer_id=_REVIEWER_ID,
        feedback=feedback,
        db=harness.db,
        persona=harness.persona,
        project_title=_PROJECT_TITLE,
        structured_feedback=harness.structured,
    )


def _state(fields: dict[str, object]) -> CarouselWorkflowState:
    return cast(CarouselWorkflowState, fields)


def _next_state() -> CarouselWorkflowState:
    return _state({
        _CURRENT_PHASE_KEY: _NEXT_PHASE,
        _PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN,
    })


@pytest.mark.unit
class TestRevisionGuards:
    """Scenario: only a revise of an existing checkpoint is capped and recorded."""

    async def test_revise_validates_the_cap_with_the_full_context(
        self, harness: _Harness
    ) -> None:
        prior = _state({_CURRENT_PHASE_KEY: PHASE_CONTENT})
        _with_states(harness, prior, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.validate_cap.assert_awaited_once_with(
            prior,
            RevisionCapValidationContext(
                project_id=_PROJECT_ID,
                project_title=_PROJECT_TITLE,
                db=harness.db,
                notifications=harness.notifications,
                structured_feedback=harness.structured,
            ),
        )

    async def test_revise_records_the_feedback_correction_exactly(
        self, harness: _Harness
    ) -> None:
        prior = _state({_CURRENT_PHASE_KEY: PHASE_CONTENT})
        _with_states(harness, prior, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.record_correction.assert_awaited_once_with(
            harness.orchestrator,
            FeedbackCorrectionContext(
                project_id=_PROJECT_ID,
                prior=prior,
                feedback=_FEEDBACK,
                persona=harness.persona,
                structured_feedback=harness.structured,
                db=harness.db,
            ),
        )

    async def test_approve_skips_the_cap_and_the_correction(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_CONTENT}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_APPROVE))
        harness.validate_cap.assert_not_awaited()
        harness.record_correction.assert_not_awaited()

    async def test_revise_without_a_checkpoint_skips_the_cap_and_the_correction(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, None, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.validate_cap.assert_not_awaited()
        harness.record_correction.assert_not_awaited()


@pytest.mark.unit
class TestReviewAndGraphInput:
    """Scenario: the review is traced and the graph gets the exact decision."""

    async def test_human_review_is_recorded_with_every_field(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_CONTENT}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_APPROVE))
        harness.record_review.assert_called_once_with(
            params=ReviewEventParams(
                phase=WORKFLOW_TRACE_PHASE_REVIEW,
                action=REVIEW_ACTION_APPROVE,
                reviewer_id=_REVIEWER_ID,
                time_to_respond=None,
                feedback=_FEEDBACK,
            ),
            project_id=_PROJECT_ID,
            user_id=_REVIEWER_ID,
        )

    async def test_graph_resume_gets_the_decision_and_a_blank_brief(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_CONTENT}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.orchestrator.resume.assert_awaited_once_with(
            _PROJECT_ID,
            {
                _ACTION_KEY: REVIEW_ACTION_REJECT,
                _REVIEWER_KEY: _REVIEWER_ID,
                _FEEDBACK_KEY: _FEEDBACK,
                STRUCTURED_FEEDBACK_KEY: harness.structured,
            },
            db=harness.db,
            workflow_input=EditorialWorkflowStartInput(
                topic="",
                audience="",
                brief="",
                sources=[],
                persona=harness.persona,
                user_id=_REVIEWER_ID,
            ),
        )

    async def test_edited_slides_are_persisted_with_the_full_command(
        self, harness: _Harness
    ) -> None:
        prior = _state({_CURRENT_PHASE_KEY: PHASE_CONTENT})
        _with_states(harness, prior, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_APPROVE))
        harness.persist_edits.assert_awaited_once_with(
            EditedSlidePersistCommand(
                db=harness.db,
                project_id=_PROJECT_ID,
                prior=prior,
                structured_feedback=harness.structured,
            )
        )


@pytest.mark.unit
class TestImageVisualFeedback:
    """Scenario: an image-phase revise stores the note as visual direction."""

    async def test_image_revise_appends_the_note(self, harness: _Harness) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_IMAGES}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.append_visual.assert_awaited_once_with(
            harness.db, _PROJECT_ID, _FEEDBACK
        )

    async def test_image_revise_without_a_note_appends_nothing(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_IMAGES}, _next_state())
        await harness.service.resume_workflow(
            _input(harness, REVIEW_ACTION_REVISE, feedback="")
        )
        harness.append_visual.assert_not_awaited()

    async def test_image_revise_without_a_session_appends_nothing(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_IMAGES}, _next_state())
        params = _input(harness, REVIEW_ACTION_REVISE)
        await harness.service.resume_workflow(
            ResumeWorkflowInput(
                project_id=params.project_id,
                action=params.action,
                reviewer_id=params.reviewer_id,
                feedback=params.feedback,
                db=None,
                persona=params.persona,
                project_title=params.project_title,
                structured_feedback=params.structured_feedback,
            )
        )
        harness.append_visual.assert_not_awaited()

    async def test_content_revise_appends_nothing(self, harness: _Harness) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_CONTENT}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.append_visual.assert_not_awaited()


@pytest.mark.unit
class TestFinalizeAfterImages:
    """Scenario: approving the images phase finalizes the carousel."""

    async def test_images_approve_finalizes_the_project(
        self, harness: _Harness
    ) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_IMAGES}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_APPROVE))
        harness.finalize.assert_awaited_once_with(harness.db, _PROJECT_ID)

    async def test_images_revise_does_not_finalize(self, harness: _Harness) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_IMAGES}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.finalize.assert_not_awaited()

    async def test_content_approve_does_not_finalize(self, harness: _Harness) -> None:
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_CONTENT}, _next_state())
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_APPROVE))
        harness.finalize.assert_not_awaited()


@pytest.mark.unit
class TestReviewEventAndSse:
    """Scenario: the review event and SSE carry the project's persisted state."""

    async def test_review_event_request_is_exact(self, harness: _Harness) -> None:
        prior = _state({_CURRENT_PHASE_KEY: PHASE_CONTENT})
        state = _next_state()
        _with_states(harness, prior, state)
        await harness.service.resume_workflow(_input(harness, REVIEW_ACTION_REVISE))
        harness.emit_review.assert_awaited_once_with(
            ReviewEventEmitRequest(
                db=harness.db,
                event_service=harness.events,
                notification_service=harness.notifications,
                context=ReviewEventEmitContext(
                    project_id=_PROJECT_ID,
                    action=REVIEW_ACTION_REVISE,
                    reviewer_id=_REVIEWER_ID,
                    feedback=_FEEDBACK,
                    prior=prior,
                    state=state,
                ),
            )
        )

    async def test_sse_is_published_for_the_project(self, harness: _Harness) -> None:
        state = _next_state()
        _with_states(harness, {_CURRENT_PHASE_KEY: PHASE_CONTENT}, state)
        result = await harness.service.resume_workflow(
            _input(harness, REVIEW_ACTION_APPROVE)
        )
        assert result is state
        harness.publish_sse.assert_awaited_once_with(_PROJECT_ID, state)
