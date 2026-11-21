"""A system retry of a blocked content gate fixes fields, it does not re-draft.

Gherkin: tests/features/content_fix_revision_ae0636.feature (section A).

Real engine + real artifact runner (the content feedback harness); the drafting model
and the field repairer are fakes. The drafts carry one over-long feature body on
slide 2, so the content gate blocks.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    feedback_history,
)
from rag_backend.application.services.carousel.content_gate_repair import (
    FieldRepairRequest,
)
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    SlideDraftGenerationParams,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    REVIEW_ACTION_REVISE,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_SOURCE_AUTOPILOT,
    FEEDBACK_STATUS_APPLIED,
    FEEDBACK_STATUS_UNCHANGED,
    STRUCTURED_FEEDBACK_SOURCE_KEY,
)
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    Review,
    drafts_for,
    localized_slide,
    park_at_content,
    review,
    state_of,
)

RETRY_NOTE = (
    "The owner asked to retry the content phase.\n"
    "Reason: content_quality.\n"
    "Revise this phase so the problem above no longer blocks it."
)
OWNER_NOTE = "Make slide 2 more concrete"
_LONG_BODY = (
    "Aplique no proximo ciclo com calma, revise cada passo com o time, registre o "
    "que mudou e compare com o ciclo anterior antes de seguir em frente."
)
_SHORT_BODY = "Aplique no proximo ciclo e compare com o anterior."
_SHORT_BODY_EN = "Apply it next cycle and compare it with the last one."
_TARGET = "2:pt:features[0].body"
_ANSWERS = {_TARGET: _SHORT_BODY, "2:en:features[0].body": _SHORT_BODY_EN}


def _blocking_drafts(generation: int) -> list[dict[str, object]]:
    drafts = drafts_for(generation)
    features = cast(list[dict[str, object]], drafts[1]["features"])
    features[0] = {**features[0], "body": _LONG_BODY}
    return drafts


class _Drafter:
    """Drafting spy: records the notes of every (re-)draft."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def __call__(
        self, _agent: object, params: SlideDraftGenerationParams
    ) -> list[dict[str, object]]:
        self.calls.append(list(params.revision_notes or []))
        return _blocking_drafts(len(self.calls))

    async def retry(self, _slide_index: int) -> dict[str, object] | None:
        return None


class _Repairer:
    """Shortens the blocked feature body once ``enabled``; records each round."""

    def __init__(self) -> None:
        self.enabled = False
        self.rounds: list[list[str]] = []

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        self.rounds.append([target.target_id for target in request.targets])
        if not self.enabled:
            return {}
        return {
            target.target_id: _ANSWERS[target.target_id]
            for target in request.targets
            if target.target_id in _ANSWERS
        }


@pytest.fixture
def drafter(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Drafter]:
    spy = _Drafter()
    monkeypatch.setattr(GENERATE_TARGET, spy)
    yield spy


def _engine(drafter: _Drafter, repairer: _Repairer) -> CarouselWorkflowEngine:
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            workflow_input=EditorialWorkflowStartInput(
                topic="Agentes", audience="devs", brief="b", sources=[]
            ),
            slide_draft_retry=drafter.retry,
            gate_repairer=repairer,
        )
    )
    return CarouselWorkflowEngine(checkpointer=InMemorySaver(), artifact_runner=runner)


def _system_retry() -> Review:
    return Review(
        action=REVIEW_ACTION_REVISE,
        feedback=RETRY_NOTE,
        structured={STRUCTURED_FEEDBACK_SOURCE_KEY: FEEDBACK_SOURCE_AUTOPILOT},
    )


def _copy(state: CarouselWorkflowState, index: int) -> list[object]:
    slide = localized_slide(state, index)
    return [slide.get("presentation_pt"), slide.get("presentation_en")]


def _history(state: CarouselWorkflowState) -> list[tuple[str, str]]:
    entries = feedback_history(state, PHASE_CONTENT)
    return [(entry["note"], entry["status"]) for entry in entries]


async def _parked(drafter: _Drafter, repairer: _Repairer) -> CarouselWorkflowEngine:
    engine = _engine(drafter, repairer)
    await park_at_content(engine)
    parked = await state_of(engine)
    assert parked["content_gate_validation"]["blocking"] is True
    return engine


@pytest.mark.unit
@pytest.mark.asyncio
class TestFixNotRework:
    async def test_system_retry_rewrites_only_the_blocked_fields(
        self, drafter: _Drafter
    ) -> None:
        """Scenario: A system retry of a blocked gate rewrites only the blocked fields"""
        repairer = _Repairer()
        engine = await _parked(drafter, repairer)
        before = await state_of(engine)
        drafts_before = len(drafter.calls)
        repairer.enabled = True
        repairer.rounds.clear()

        await review(engine, _system_retry())

        state = await state_of(engine)
        assert len(drafter.calls) == drafts_before
        assert repairer.rounds and _TARGET in repairer.rounds[0]
        pt = cast(dict[str, object], localized_slide(state, 2)["presentation_pt"])
        features = cast(list[dict[str, object]], pt["features"])
        assert features[0]["body"] == _SHORT_BODY
        for index in (1, 3):
            assert _copy(state, index) == _copy(before, index)
        assert state["content_gate_validation"].get("blocking") is not True
        assert validate_localized_slides(state["localized_slides"]).blocking is False
        assert _history(state) == [(RETRY_NOTE, FEEDBACK_STATUS_APPLIED)]

    async def test_fix_that_changes_nothing_keeps_the_deck(
        self, drafter: _Drafter
    ) -> None:
        """Scenario: A fix that changes nothing keeps the deck and records the note unchanged"""
        engine = await _parked(drafter, _Repairer())
        before = await state_of(engine)
        drafts_before = len(drafter.calls)

        await review(engine, _system_retry())

        state = await state_of(engine)
        assert len(drafter.calls) == drafts_before
        assert state["localized_slides"] == before["localized_slides"]
        assert _history(state) == [(RETRY_NOTE, FEEDBACK_STATUS_UNCHANGED)]

    async def test_owner_note_still_redrafts(self, drafter: _Drafter) -> None:
        """Scenario: An owner's own revise note still re-drafts the content"""
        engine = await _parked(drafter, _Repairer())
        drafts_before = len(drafter.calls)

        await review(engine, Review(action=REVIEW_ACTION_REVISE, feedback=OWNER_NOTE))

        assert len(drafter.calls) == drafts_before + 1
        assert drafter.calls[-1][0] == OWNER_NOTE
