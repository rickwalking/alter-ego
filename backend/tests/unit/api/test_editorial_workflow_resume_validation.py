"""Unit tests for AE-0310 resume validation: uncapped edits + charged phase.

Feature: Design-step recovery from content-level violations
(see features/carousel_design_phase_recovery.feature)

Scenario Outline: Send-backs consume the target phase's revision budget
Scenario: Direct edits remain available after all caps are exhausted
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    _ResumeGateContext,
    validate_resume_action,
    validate_resume_workflow_gates,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialStructuredFeedback,
    EditorialWorkflowResumeRequest,
    LocalizedSlideReview,
)
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_REVISION_CAP_PER_PHASE,
    ERR_REVISE_FEEDBACK_REQUIRED,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    REVIEW_ACTION_REVISE,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError


def _edited_slides_feedback() -> EditorialStructuredFeedback:
    return EditorialStructuredFeedback(
        edited_localized_slides=[
            LocalizedSlideReview(slide_index=4, slide_type="hero_content")
        ]
    )


def _request(
    feedback: str | None,
    structured: EditorialStructuredFeedback | None,
) -> EditorialWorkflowResumeRequest:
    return EditorialWorkflowResumeRequest(
        action=REVIEW_ACTION_REVISE,
        feedback=feedback,
        expected_version=1,
        structured_feedback=structured,
    )


def _gate_ctx() -> _ResumeGateContext:
    return _ResumeGateContext(
        db=None,  # type: ignore[arg-type]
        project_id="38affb3e",
        project_title="Prod carousel",
    )


@pytest.mark.unit
class TestValidateResumeAction:
    """An edited-slides submission is a complete revise without feedback."""

    def test_revise_with_edits_and_no_feedback_is_accepted(self) -> None:
        request = _request(None, _edited_slides_feedback())

        assert validate_resume_action(request) == ""

    def test_revise_without_edits_still_requires_feedback(self) -> None:
        request = _request("   ", None)

        with pytest.raises(HTTPException) as exc:
            validate_resume_action(request)
        assert exc.value.detail == ERR_REVISE_FEEDBACK_REQUIRED


@pytest.mark.unit
class TestResumeGatesCapAccounting:
    """The 409 conflict names the CHARGED phase (target on a send-back)."""

    @pytest.mark.parametrize("source", [PHASE_DESIGN, PHASE_FINAL_REVIEW])
    async def test_send_back_conflict_names_target_phase(self, source: str) -> None:
        workflow_state = {
            "current_phase": source,
            "revision_count": {PHASE_CONTENT: DEFAULT_REVISION_CAP_PER_PHASE},
        }
        request = _request(
            "Regenerate slide 4",
            EditorialStructuredFeedback(target_phase=PHASE_CONTENT),
        )

        with pytest.raises(CarouselConflictError) as exc:
            await validate_resume_workflow_gates(
                request,
                workflow_state,  # type: ignore[arg-type]
                ctx=_gate_ctx(),
            )
        assert exc.value.conflict.phase == PHASE_CONTENT

    async def test_edited_slides_bypass_exhausted_caps(self) -> None:
        """Scenario: Direct edits remain available after all caps are
        exhausted."""
        workflow_state = {
            "current_phase": PHASE_DESIGN,
            "revision_count": {
                PHASE_CONTENT: DEFAULT_REVISION_CAP_PER_PHASE,
                PHASE_DESIGN: DEFAULT_REVISION_CAP_PER_PHASE,
            },
        }
        request = _request(None, _edited_slides_feedback())

        await validate_resume_workflow_gates(
            request,
            workflow_state,  # type: ignore[arg-type]
            ctx=_gate_ctx(),
        )  # no raise
