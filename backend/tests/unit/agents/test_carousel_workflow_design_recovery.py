"""Unit tests for design-phase dead-end recovery (AE-0310).

Feature: Design-step recovery from content-level violations
(see features/carousel_design_phase_recovery.feature)

Scenario: Reviewer edits the flagged slide in place at design
Scenario: Reviewer sends the workflow back to content from design
Scenario: Plain design revise re-validates instead of looping

The prod-shaped fixture mirrors project 38affb3e: slide 4 carries a blocking
``drafting_scaffold_present`` violation discovered at the design step while
generated images already exist.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from rag_backend.agents.carousel_workflow_graph import (
    route_after_design,
    route_after_gate,
)
from rag_backend.agents.carousel_workflow_nodes import (
    design_phase,
    review_updates_from_response,
)
from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
)
from rag_backend.application.services.carousel.workflow_state import (
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel_workflow import (
    DESIGN_VALIDATION_RECOVERY_HINT,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    SEND_BACK_TARGET_PHASE_KEY,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_DESIGN_RECOVERY_HINT,
    STATE_FIELD_PRESENTATION_VALIDATION,
)

_SLIDE_TYPE = "hero_content"
_SCAFFOLD_BODY = "SLIDE 4: rascunho com scaffold TITLE: pendente"
_FIXED_BODY = "Corpo corrigido do slide quatro."


def _localized_slide(index: int, body_pt: str) -> dict[str, object]:
    return {
        "slide_index": index,
        "slide_type": _SLIDE_TYPE,
        "presentation_pt": {
            "slide_type": _SLIDE_TYPE,
            "heading": f"Titulo {index}",
            "body": body_pt,
        },
        "presentation_en": {
            "slide_type": _SLIDE_TYPE,
            "heading": f"Title {index}",
            "body": f"Body {index}",
        },
    }


def _prod_shaped_design_state(**overrides: object) -> dict[str, object]:
    """Prod-shaped 38affb3e state: blocking slide 4 parked at design."""
    state = get_initial_carousel_state("38affb3e", {"topic": "AI"})
    state.update({
        "current_phase": PHASE_DESIGN,
        "content_approved": True,
        "design_applied": True,
        "image_assets": [f"slide_{index}.jpg" for index in range(1, 5)],
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [
            _localized_slide(1, "Corpo 1"),
            _localized_slide(4, _SCAFFOLD_BODY),
        ],
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: {
            "validation_status": "invalid",
            "validated_at": "2026-07-07T00:00:00Z",
            "blocking": True,
            "violations": [
                {"code": "drafting_scaffold_present", "slide_index": 4},
            ],
        },
    })
    state.update(overrides)  # type: ignore[typeddict-item]
    return dict(state)


@pytest.mark.unit
class TestDesignSendBackToContent:
    """Scenario: Reviewer sends the workflow back to content from design."""

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_design_send_back_re_enters_content(self, mock_interrupt: object) -> None:
        """A design revise targeting content keeps current_phase=content,
        preserves the routing target, and resets content_approved."""
        mock_interrupt.return_value = {
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT,
            },
        }

        result = design_phase(_prod_shaped_design_state())  # type: ignore[arg-type]

        assert result["current_phase"] == PHASE_CONTENT
        assert result[SEND_BACK_TARGET_PHASE_KEY] == PHASE_CONTENT
        assert result["content_approved"] is False
        assert result["design_approved"] is False

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_design_send_back_preserves_generated_images(
        self, mock_interrupt: object
    ) -> None:
        """Image assets are untouched by the send-back updates — preservation
        for unchanged outline headings rides the prompt-hash reuse, so the
        node must not clear them."""
        mock_interrupt.return_value = {
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT,
            },
        }

        result = design_phase(_prod_shaped_design_state())  # type: ignore[arg-type]

        assert "image_assets" not in result
        # post_review must not force design_applied on a send-back either.
        assert "design_applied" not in result

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_plain_design_revise_clears_stale_send_back_target(
        self, mock_interrupt: object
    ) -> None:
        """A plain revise clears a stale target from a prior cycle so it
        cannot re-route the retry loop back to content."""
        mock_interrupt.return_value = {"action": REVIEW_ACTION_REVISE}

        result = design_phase(
            _prod_shaped_design_state(**{SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT})  # type: ignore[arg-type]
        )

        assert result["current_phase"] == PHASE_DESIGN
        assert result[SEND_BACK_TARGET_PHASE_KEY] == ""

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_design_approve_still_applies_post_review(
        self, mock_interrupt: object
    ) -> None:
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}

        result = design_phase(_prod_shaped_design_state())  # type: ignore[arg-type]

        assert result["design_approved"] is True
        assert result["design_applied"] is True
        assert result["current_phase"] == PHASE_DESIGN


@pytest.mark.unit
class TestDesignEditedSlides:
    """Scenario: Reviewer edits the flagged slide in place at design."""

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_edited_slides_applied_and_revalidated_at_design(
        self, mock_interrupt: object
    ) -> None:
        """Edits submitted from design update localized_slides and store a
        fresh non-blocking validation report (uniform apply semantics)."""
        mock_interrupt.return_value = {
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [
                    _localized_slide(4, _FIXED_BODY),
                ],
            },
        }

        result = design_phase(_prod_shaped_design_state())  # type: ignore[arg-type]

        slides = result[WORKFLOW_STATE_LOCALIZED_SLIDES_KEY]
        assert isinstance(slides, list)
        edited = next(slide for slide in slides if slide.get("slide_index") == 4)
        pt_payload = edited["presentation_pt"]
        assert isinstance(pt_payload, dict)
        assert pt_payload["body"] == _FIXED_BODY
        validation = result[WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY]
        assert isinstance(validation, dict)
        assert validation["blocking"] is False

    def test_edited_slides_accepted_at_final_review_node(self) -> None:
        """The node helper honors edits at final_review too (widened set)."""
        state = _prod_shaped_design_state(current_phase=PHASE_FINAL_REVIEW)
        updates = review_updates_from_response(
            {
                "action": REVIEW_ACTION_APPROVE,
                STRUCTURED_FEEDBACK_KEY: {
                    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [
                        _localized_slide(4, _FIXED_BODY),
                    ],
                },
            },
            state=state,  # type: ignore[arg-type]
            phase=PHASE_FINAL_REVIEW,
        )

        assert WORKFLOW_STATE_LOCALIZED_SLIDES_KEY in updates

    def test_edited_slides_ignored_outside_allowed_phases(self) -> None:
        """The node helper still short-circuits off the allowlist (images)."""
        state = _prod_shaped_design_state(current_phase=PHASE_IMAGES)
        updates = review_updates_from_response(
            {
                "action": REVIEW_ACTION_APPROVE,
                STRUCTURED_FEEDBACK_KEY: {
                    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [
                        _localized_slide(4, _FIXED_BODY),
                    ],
                },
            },
            state=state,  # type: ignore[arg-type]
            phase=PHASE_IMAGES,
        )

        assert WORKFLOW_STATE_LOCALIZED_SLIDES_KEY not in updates


@pytest.mark.unit
class TestRouteAfterDesign:
    """Routing for the widened design gate."""

    def test_route_after_design_approved_goes_to_images(self) -> None:
        state = _prod_shaped_design_state(design_approved=True)
        assert route_after_design(state) == "approved"  # type: ignore[arg-type]

    def test_route_after_design_send_back_goes_to_content(self) -> None:
        state = _prod_shaped_design_state(
            design_approved=False,
            **{SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT},
        )
        assert route_after_design(state) == PHASE_CONTENT  # type: ignore[arg-type]

    def test_route_after_design_plain_revise_retries_design(self) -> None:
        state = _prod_shaped_design_state(
            design_approved=False,
            **{SEND_BACK_TARGET_PHASE_KEY: ""},
        )
        assert route_after_design(state) == "retry"  # type: ignore[arg-type]

    def test_route_after_design_ignores_disallowed_target(self) -> None:
        state = _prod_shaped_design_state(
            design_approved=False,
            **{SEND_BACK_TARGET_PHASE_KEY: PHASE_IMAGES},
        )
        assert route_after_design(state) == "retry"  # type: ignore[arg-type]

    def test_route_after_gate_unchanged_for_other_phases(self) -> None:
        state = _prod_shaped_design_state(outline_approved=True)
        assert route_after_gate(state, "outline_approved") == "approved"  # type: ignore[arg-type]


@pytest.mark.unit
class TestDesignInterruptPayload:
    """Scenario: Plain design revise re-validates instead of looping —
    the re-interrupt carries the fresh report plus the recovery hint."""

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    def test_design_interrupt_payload_carries_report_and_hint(
        self, mock_interrupt: object
    ) -> None:
        mock_interrupt.return_value = {"action": REVIEW_ACTION_REVISE}
        state = _prod_shaped_design_state(**{
            STATE_FIELD_DESIGN_RECOVERY_HINT: DESIGN_VALIDATION_RECOVERY_HINT
        })

        design_phase(state)  # type: ignore[arg-type]

        payload = mock_interrupt.call_args[0][0]
        validation = payload[STATE_FIELD_PRESENTATION_VALIDATION]
        assert validation["blocking"] is True
        assert (
            payload[STATE_FIELD_DESIGN_RECOVERY_HINT] == DESIGN_VALIDATION_RECOVERY_HINT
        )
