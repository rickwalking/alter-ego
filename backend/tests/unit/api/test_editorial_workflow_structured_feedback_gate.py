"""Unit tests for the structured-feedback phase gate (AE-0290).

Covers ``ensure_structured_feedback_allowed`` — the gate that decides whether a
resume's structured-feedback fields are permitted at the current checkpoint phase.
The AE-0290 fix makes a final-review send-back record ``current_phase=content`` so
the two-step edited-slides flow (send back, then edit at content) is unblocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    ensure_structured_feedback_allowed,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialStructuredFeedback,
    EditorialWorkflowResumeRequest,
    LocalizedSlideReview,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED,
    ERR_SEND_BACK_TARGET_NOT_ALLOWED,
    ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    REVIEW_ACTION_REVISE,
)


def _service(checkpoint_phase: str) -> AsyncMock:
    service = AsyncMock()
    service.read_checkpoint_phase = AsyncMock(return_value=checkpoint_phase)
    return service


def _request(feedback: EditorialStructuredFeedback) -> EditorialWorkflowResumeRequest:
    return EditorialWorkflowResumeRequest(
        action=REVIEW_ACTION_REVISE,
        expected_version=1,
        structured_feedback=feedback,
    )


@pytest.mark.unit
class TestStructuredFeedbackGate:
    async def test_target_phase_send_back_accepted_at_final_review(self) -> None:
        """AE-0290 regression: a target_phase send-back is accepted while the
        checkpoint is final_review (the gate does not block it)."""
        service = _service(PHASE_FINAL_REVIEW)
        request = _request(EditorialStructuredFeedback(target_phase=PHASE_CONTENT))

        await ensure_structured_feedback_allowed(
            service, "project-1", request
        )  # no raise

    async def test_edited_slides_accepted_once_checkpoint_is_content(self) -> None:
        """After the fix parks the workflow at content, edited slides are accepted."""
        service = _service(PHASE_CONTENT)
        request = _request(
            EditorialStructuredFeedback(
                edited_localized_slides=[
                    LocalizedSlideReview(slide_index=1, slide_type="intro")
                ]
            )
        )

        await ensure_structured_feedback_allowed(
            service, "project-1", request
        )  # no raise

    async def test_edited_slides_accepted_at_design_and_final_review(self) -> None:
        """AE-0310: the edited-slides allowlist is widened to
        {content, design, final_review} — all three phases accept edits."""
        for phase in (PHASE_DESIGN, PHASE_FINAL_REVIEW):
            service = _service(phase)
            request = _request(
                EditorialStructuredFeedback(
                    edited_localized_slides=[
                        LocalizedSlideReview(slide_index=1, slide_type="intro")
                    ]
                )
            )

            await ensure_structured_feedback_allowed(
                service, "project-1", request
            )  # no raise

    async def test_edited_slides_rejected_at_images_checkpoint(self) -> None:
        """AE-0310: edits stay rejected outside {content, design, final_review}
        (images), with the renamed phase-not-allowed error."""
        service = _service(PHASE_IMAGES)
        request = _request(
            EditorialStructuredFeedback(
                edited_localized_slides=[
                    LocalizedSlideReview(slide_index=1, slide_type="intro")
                ]
            )
        )

        with pytest.raises(HTTPException) as exc:
            await ensure_structured_feedback_allowed(service, "project-1", request)
        assert exc.value.detail == ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED

    async def test_design_send_back_to_content_accepted(self) -> None:
        """AE-0310: a design revise may target content (send-back)."""
        service = _service(PHASE_DESIGN)
        request = _request(EditorialStructuredFeedback(target_phase=PHASE_CONTENT))

        await ensure_structured_feedback_allowed(
            service, "project-1", request
        )  # no raise

    async def test_design_send_back_to_outline_rejected(self) -> None:
        """AE-0310: design send-backs are limited to content."""
        service = _service(PHASE_DESIGN)
        request = _request(EditorialStructuredFeedback(target_phase=PHASE_OUTLINE))

        with pytest.raises(HTTPException) as exc:
            await ensure_structured_feedback_allowed(service, "project-1", request)
        assert exc.value.detail == ERR_SEND_BACK_TARGET_NOT_ALLOWED

    async def test_target_phase_rejected_at_content_checkpoint(self) -> None:
        """target_phase stays rejected at phases without send-back support."""
        service = _service(PHASE_CONTENT)
        request = _request(EditorialStructuredFeedback(target_phase=PHASE_OUTLINE))

        with pytest.raises(HTTPException) as exc:
            await ensure_structured_feedback_allowed(service, "project-1", request)
        assert exc.value.detail == ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY

    async def test_edited_text_rejected_at_design(self) -> None:
        """AE-0310: edited_text remains final-review-only."""
        service = _service(PHASE_DESIGN)
        request = _request(EditorialStructuredFeedback(edited_text="Caption"))

        with pytest.raises(HTTPException) as exc:
            await ensure_structured_feedback_allowed(service, "project-1", request)
        assert exc.value.detail == ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY
