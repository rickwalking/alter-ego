"""Unit tests for target-aware revision-cap accounting (AE-0310).

Feature: Design-step recovery from content-level violations
(see features/carousel_design_phase_recovery.feature)

Scenario Outline: Send-backs consume the target phase's revision budget
Scenario: Direct edits remain available after all caps are exhausted
Scenario: Plain design revise while blocking consumes no design budget
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    ResumeContext,
    RevisionCapValidationContext,
    prepare_resume_workflow,
    resolve_revision_cap_phase,
    validate_revision_cap,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_REVISION_CAP_PER_PHASE,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)

_SLIDE_TYPE = "hero_content"
_SCAFFOLD_BODY = "SLIDE 4: rascunho com scaffold TITLE: pendente"


def _blocking_localized_slides() -> list[dict[str, object]]:
    return [
        {
            "slide_index": 4,
            "slide_type": _SLIDE_TYPE,
            "presentation_pt": {
                "slide_type": _SLIDE_TYPE,
                "heading": "Titulo 4",
                "body": _SCAFFOLD_BODY,
            },
            "presentation_en": {
                "slide_type": _SLIDE_TYPE,
                "heading": "Title 4",
                "body": "Body 4",
            },
        }
    ]


def _prior(
    phase: str,
    revision_count: dict[str, int],
    *,
    blocking: bool = False,
) -> CarouselWorkflowState:
    state: dict[str, object] = {
        "current_phase": phase,
        "revision_count": revision_count,
    }
    if blocking:
        state["localized_slides"] = _blocking_localized_slides()
    return cast(CarouselWorkflowState, state)


def _send_back(target: str) -> dict[str, object]:
    return {STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: target}


def _edits() -> dict[str, object]:
    return {STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [{"slide_index": 4}]}


def _ctx(structured_feedback: dict[str, object] | None) -> RevisionCapValidationContext:
    return RevisionCapValidationContext(
        project_id="38affb3e",
        project_title="Prod carousel",
        structured_feedback=structured_feedback,
    )


@pytest.mark.unit
class TestResolveRevisionCapPhase:
    """The cap charges the phase whose LLM re-runs; human edits charge none."""

    def test_design_send_back_charges_content(self) -> None:
        prior = _prior(PHASE_DESIGN, {})
        assert (
            resolve_revision_cap_phase(prior, _send_back(PHASE_CONTENT))
            == PHASE_CONTENT
        )

    def test_final_review_send_back_charges_content(self) -> None:
        """Regression for the pre-existing final_review→content divergence:
        the check now evaluates the TARGET phase like the increment does."""
        prior = _prior(PHASE_FINAL_REVIEW, {})
        assert (
            resolve_revision_cap_phase(prior, _send_back(PHASE_CONTENT))
            == PHASE_CONTENT
        )

    def test_edited_slides_charge_no_phase(self) -> None:
        prior = _prior(PHASE_DESIGN, {})
        assert resolve_revision_cap_phase(prior, _edits()) is None

    def test_edits_with_target_charge_the_target(self) -> None:
        prior = _prior(PHASE_DESIGN, {})
        structured = {**_send_back(PHASE_CONTENT), **_edits()}
        assert resolve_revision_cap_phase(prior, structured) == PHASE_CONTENT

    def test_plain_design_revise_while_blocking_charges_no_phase(self) -> None:
        """A design revise with a blocking report is a provable content no-op
        (re-validate + re-interrupt), so it must not burn the design budget."""
        prior = _prior(PHASE_DESIGN, {}, blocking=True)
        assert resolve_revision_cap_phase(prior, None) is None

    def test_plain_design_revise_without_blocking_charges_design(self) -> None:
        prior = _prior(PHASE_DESIGN, {})
        assert resolve_revision_cap_phase(prior, None) == PHASE_DESIGN

    def test_plain_content_revise_charges_content(self) -> None:
        prior = _prior(PHASE_CONTENT, {})
        assert resolve_revision_cap_phase(prior, None) == PHASE_CONTENT


@pytest.mark.unit
class TestValidateRevisionCapTargetAware:
    """Scenario Outline: Send-backs consume the target phase's budget."""

    @pytest.mark.parametrize("source", [PHASE_DESIGN, PHASE_FINAL_REVIEW])
    async def test_send_back_rejected_when_content_cap_exhausted(
        self, source: str
    ) -> None:
        prior = _prior(
            source,
            {PHASE_CONTENT: DEFAULT_REVISION_CAP_PER_PHASE, source: 0},
        )

        with pytest.raises(ValueError, match=ERR_REVISION_CAP_EXCEEDED):
            await validate_revision_cap(prior, _ctx(_send_back(PHASE_CONTENT)))

    @pytest.mark.parametrize("source", [PHASE_DESIGN, PHASE_FINAL_REVIEW])
    async def test_send_back_allowed_with_content_budget_remaining(
        self, source: str
    ) -> None:
        prior = _prior(
            source,
            {
                PHASE_CONTENT: DEFAULT_REVISION_CAP_PER_PHASE - 1,
                source: DEFAULT_REVISION_CAP_PER_PHASE,
            },
        )

        await validate_revision_cap(prior, _ctx(_send_back(PHASE_CONTENT)))

    async def test_edited_slides_pass_with_all_caps_exhausted(self) -> None:
        """Scenario: Direct edits remain available after all caps are
        exhausted — the guaranteed escape hatch is never cap-blocked."""
        prior = _prior(
            PHASE_DESIGN,
            {
                PHASE_CONTENT: DEFAULT_REVISION_CAP_PER_PHASE,
                PHASE_DESIGN: DEFAULT_REVISION_CAP_PER_PHASE,
            },
            blocking=True,
        )

        await validate_revision_cap(prior, _ctx(_edits()))

    async def test_plain_design_revise_while_blocking_skips_cap(self) -> None:
        prior = _prior(
            PHASE_DESIGN,
            {PHASE_DESIGN: DEFAULT_REVISION_CAP_PER_PHASE},
            blocking=True,
        )

        await validate_revision_cap(prior, _ctx(None))

    async def test_plain_revise_still_capped_on_current_phase(self) -> None:
        prior = _prior(PHASE_CONTENT, {PHASE_CONTENT: DEFAULT_REVISION_CAP_PER_PHASE})

        with pytest.raises(ValueError, match=ERR_REVISION_CAP_EXCEEDED):
            await validate_revision_cap(prior, _ctx(None))


@pytest.mark.unit
class TestUncappedSubmissionsDoNotIncrement:
    """Scenario: Plain design revise while blocking consumes no design budget."""

    @staticmethod
    def _orchestrator() -> MagicMock:
        orchestrator = MagicMock()
        orchestrator.engine = MagicMock()
        orchestrator.engine.update_state = AsyncMock()
        return orchestrator

    async def test_blocking_design_revise_stores_note_without_increment(
        self,
    ) -> None:
        orchestrator = self._orchestrator()
        prior = _prior(PHASE_DESIGN, {PHASE_DESIGN: 2}, blocking=True)

        await prepare_resume_workflow(
            ResumeContext(
                orchestrator=orchestrator,
                project_id="38affb3e",
                action=REVIEW_ACTION_REVISE,
                prior=prior,
                feedback="Slide 4 still shows scaffold text",
                structured_feedback=None,
            ),
        )

        update = orchestrator.engine.update_state.await_args.args[1]
        assert update["phase_feedback"][PHASE_DESIGN] == [
            "Slide 4 still shows scaffold text"
        ]
        assert "revision_count" not in update

    async def test_design_send_back_increments_content_counter(self) -> None:
        orchestrator = self._orchestrator()
        prior = _prior(PHASE_DESIGN, {PHASE_CONTENT: 1}, blocking=True)

        await prepare_resume_workflow(
            ResumeContext(
                orchestrator=orchestrator,
                project_id="38affb3e",
                action=REVIEW_ACTION_REVISE,
                prior=prior,
                feedback="Regenerate slide 4 without scaffold",
                structured_feedback=_send_back(PHASE_CONTENT),
            ),
        )

        update = orchestrator.engine.update_state.await_args.args[1]
        assert update["revision_count"][PHASE_CONTENT] == 2
        assert update["phase_feedback"][PHASE_CONTENT] == [
            "Regenerate slide 4 without scaffold"
        ]
