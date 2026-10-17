"""AE-0413: manual fixes on the content gate (REPORT B02 + B03).

Gherkin: tests/features/content_gate_backend_ae0413.feature

Real engine + real artifact runner on an in-memory checkpointer (the AE-0405
harness); the drafting model is a spy. The exact QA sequence: research ->
outline -> content, then "Submit manual fixes" on the FIRST content gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import ClassVar, cast
from unittest.mock import AsyncMock

import pytest

from rag_backend.agents.carousel_content_park import manual_fixes_park_updates
from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    ensure_structured_feedback_allowed,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialStructuredFeedback,
    EditorialWorkflowResumeRequest,
    LocalizedSlideReview,
)
from rag_backend.application.services.carousel.editorial_workflow_feedback import (
    read_checkpoint_phase,
)
from rag_backend.domain.carousel_gate_phase import checkpoint_gate_phase
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    SEND_BACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.content_feedback import (
    STATE_FIELD_CONTENT_ARTIFACTS_PARKED,
)
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    PROJECT_ID,
    DraftingModel,
    Review,
    build_engine,
    edited_slide,
    localized_slide,
    manual_fixes,
    park_at_content,
    review,
    state_of,
)


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> Iterator[DraftingModel]:
    spy = DraftingModel()
    monkeypatch.setattr(GENERATE_TARGET, spy)
    yield spy


async def _stored_phase(engine: CarouselWorkflowEngine) -> str:
    snapshot = await engine._app.aget_state(engine._run_config(PROJECT_ID))
    return str(snapshot.values.get("current_phase", ""))


def _resume_request(slide: dict[str, object]) -> EditorialWorkflowResumeRequest:
    return EditorialWorkflowResumeRequest(
        action=REVIEW_ACTION_REVISE,
        expected_version=1,
        structured_feedback=EditorialStructuredFeedback(
            edited_localized_slides=[
                LocalizedSlideReview.model_validate({**slide, "slide_type": "content"})
            ]
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestFirstContentGatePhase:
    async def test_checkpoint_phase_is_content_on_first_content_gate(
        self, model: DraftingModel
    ) -> None:
        """Scenario: Manual fixes are accepted on the first content gate (B02)."""
        engine = build_engine(model)
        await park_at_content(engine)

        assert await read_checkpoint_phase(engine, PROJECT_ID) == PHASE_CONTENT
        assert (await state_of(engine))["current_phase"] == PHASE_CONTENT

    async def test_parked_checkpoint_stores_content_phase(
        self, model: DraftingModel
    ) -> None:
        """Scenario: The parked content checkpoint names the content gate."""
        engine = build_engine(model)
        await park_at_content(engine)

        assert await _stored_phase(engine) == PHASE_CONTENT

    async def test_structured_feedback_guard_accepts_edits_on_first_gate(
        self, model: DraftingModel
    ) -> None:
        """Scenario: Manual fixes are accepted on the first content gate (guard)."""
        engine = build_engine(model)
        await park_at_content(engine)
        service = AsyncMock()

        async def _phase(project_id: str) -> str:
            return await read_checkpoint_phase(engine, project_id)

        service.read_checkpoint_phase = _phase
        request = _resume_request(edited_slide(await state_of(engine), 2))

        await ensure_structured_feedback_allowed(service, PROJECT_ID, request)


@pytest.mark.unit
class TestCheckpointGatePhase:
    """Scenario: The approved-hold park keeps the final_review phase."""

    @pytest.mark.parametrize(
        ("stored", "pending", "expected"),
        [
            (PHASE_OUTLINE, (PHASE_CONTENT,), PHASE_CONTENT),
            (PHASE_IMAGES, (PHASE_FINAL_REVIEW,), PHASE_FINAL_REVIEW),
            (PHASE_CONTENT, (PHASE_DESIGN,), PHASE_DESIGN),
            (PHASE_FINAL_REVIEW, (PHASE_APPROVED_HOLD,), PHASE_FINAL_REVIEW),
            (PHASE_CONTENT, (), PHASE_CONTENT),
            (PHASE_CONTENT, ("__unknown_node__",), PHASE_CONTENT),
        ],
    )
    def test_gate_phase(
        self, stored: str, pending: tuple[str, ...], expected: str
    ) -> None:
        snapshot = SimpleNamespace(values={"current_phase": stored}, next=pending)

        assert checkpoint_gate_phase(snapshot) == expected

    def test_snapshot_without_values_has_no_phase(self) -> None:
        assert checkpoint_gate_phase(SimpleNamespace(values=None, next=())) == ""

    async def test_missing_snapshot_reads_empty_phase(self) -> None:
        engine = SimpleNamespace(
            _run_config=lambda _project_id: {},
            _app=SimpleNamespace(aget_state=AsyncMock(return_value=None)),
        )

        phase = await read_checkpoint_phase(
            cast(CarouselWorkflowEngine, engine), PROJECT_ID
        )

        assert phase == ""


@pytest.mark.unit
@pytest.mark.asyncio
class TestManualFixesOnFirstGate:
    async def test_manual_fixes_keep_edits_without_regenerating(
        self, model: DraftingModel
    ) -> None:
        """Scenario: Manual fixes on the first content gate keep the edited copy (B03).

        Before AE-0413 the revise re-entered the content node and its ensure
        rebuilt every localized slide from the PT drafts (EN fell back to PT,
        structured items dropped) and re-drafted blocking slides.
        """
        engine = build_engine(model)
        await park_at_content(engine)
        before = await state_of(engine)
        ensures = model.content_ensures
        edit = edited_slide(before, 2)

        await review(engine, manual_fixes(edit))

        state = await state_of(engine)
        assert model.content_ensures == ensures
        assert model.calls == [[]]
        assert model.retries == []
        slide = localized_slide(state, 2)
        assert slide["presentation_pt"] == edit["presentation_pt"]
        assert slide["presentation_en"] == edit["presentation_en"]
        for index in (1, 3, 4, 5, 6, 7):
            assert localized_slide(state, index) == localized_slide(before, index)
        assert state["current_phase"] == PHASE_CONTENT
        assert state[STATE_FIELD_CONTENT_ARTIFACTS_PARKED] is True
        assert (
            state["presentation_validation"]["validated_at"]
            != (before["presentation_validation"]["validated_at"])
        )

    async def test_two_manual_fixes_in_a_row_never_regenerate(
        self, model: DraftingModel
    ) -> None:
        """Scenario: Manual fixes on the first content gate keep the edited copy (twice)."""
        engine = build_engine(model)
        await park_at_content(engine)
        ensures = model.content_ensures
        await review(engine, manual_fixes(edited_slide(await state_of(engine), 2)))
        second = edited_slide(await state_of(engine), 3)

        await review(engine, manual_fixes(second))

        state = await state_of(engine)
        assert model.content_ensures == ensures
        assert localized_slide(state, 3)["presentation_en"] == second["presentation_en"]

    async def test_approve_after_manual_fix_commits_the_edit(
        self, model: DraftingModel
    ) -> None:
        """Scenario: A manual fix followed by approval commits the edited copy."""
        engine = build_engine(model)
        await park_at_content(engine)
        edit = edited_slide(await state_of(engine), 2)
        await review(engine, manual_fixes(edit))

        await review(engine, Review(action=REVIEW_ACTION_APPROVE))

        state = await state_of(engine)
        assert model.calls == [[]]
        assert state["current_phase"] == PHASE_DESIGN
        assert localized_slide(state, 2)["presentation_pt"] == edit["presentation_pt"]
        assert state[STATE_FIELD_CONTENT_ARTIFACTS_PARKED] is False

    async def test_feedback_with_edits_still_regenerates(
        self, model: DraftingModel
    ) -> None:
        """A revise carrying a note AND edits regenerates with that note."""
        engine = build_engine(model)
        await park_at_content(engine)
        edit = edited_slide(await state_of(engine), 2)
        decision = manual_fixes(edit)

        await review(
            engine,
            Review(
                action=REVIEW_ACTION_REVISE,
                feedback="EN em inglês",
                structured=decision.structured,
            ),
        )

        assert model.calls == [[], ["EN em inglês"]]


@pytest.mark.unit
class TestManualFixesParkUpdates:
    """The manual-fixes decision on one finished content review (AE-0413)."""

    _EDITS: ClassVar[dict[str, object]] = {
        "phase_status": "awaiting_human",
        "localized_slides": [{"slide_index": 2}],
    }

    @pytest.mark.parametrize(
        "state",
        [
            {},
            {"phase_feedback": "not-a-map"},
            {"phase_feedback": {"content": "not-a-list"}},
            {"phase_feedback": {"content": ["  "], "research": ["note"]}},
        ],
    )
    def test_edits_only_revise_keeps_the_edits(self, state: dict[str, object]) -> None:
        assert manual_fixes_park_updates(self._EDITS, state) == {
            STATE_FIELD_CONTENT_ARTIFACTS_PARKED: True
        }

    @pytest.mark.parametrize(
        ("review_update", "state"),
        [
            ({**_EDITS, "phase_status": "approved"}, {}),
            ({"phase_status": "awaiting_human"}, {}),
            ({**_EDITS, SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT}, {}),
            (_EDITS, {"phase_feedback": {"content": ["EN em inglês"]}}),
        ],
    )
    def test_other_reviews_run_the_content_ensure(
        self, review_update: dict[str, object], state: dict[str, object]
    ) -> None:
        assert manual_fixes_park_updates(review_update, state) == {}
