"""AE-0430: a content revision carries the gate's violations and is repaired after.

Gherkin: tests/features/content_gate_repair_ae0430.feature (section B).

Real engine + real artifact runner (the AE-0405 harness); the drafting model
and the field repairer are fakes. The drafts carry one over-long feature body,
so the content gate blocks.
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
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    REVIEW_ACTION_REVISE,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_STATUS_APPLIED,
    FEEDBACK_STATUS_UNCHANGED,
)
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REVISION_NOTE_HEADER,
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

NOTE = "Fix them: Slides para corrigir: Slide 2"
_LONG_BODY = (
    "Aplique no proximo ciclo com calma, revise cada passo com o time, registre o "
    "que mudou e compare com o ciclo anterior antes de seguir em frente."
)
_SHORT_BODY = "Aplique no proximo ciclo e compare com o anterior."


def _blocking_drafts(generation: int) -> list[dict[str, object]]:
    drafts = drafts_for(generation)
    features = cast(list[dict[str, object]], drafts[1]["features"])
    features[0] = {**features[0], "body": _LONG_BODY}
    return drafts


class _Drafter:
    """Drafting spy; ``same`` returns identical drafts every generation."""

    def __init__(self, *, same: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.same = same

    async def __call__(
        self, _agent: object, params: SlideDraftGenerationParams
    ) -> list[dict[str, object]]:
        self.calls.append(list(params.revision_notes or []))
        return _blocking_drafts(1 if self.same else len(self.calls))

    async def retry(self, _slide_index: int) -> dict[str, object] | None:
        return None


class _Repairer:
    """Fixes the feature body only once ``enabled``; records each round."""

    def __init__(self) -> None:
        self.enabled = False
        self.rounds: list[list[str]] = []

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        self.rounds.append([target.target_id for target in request.targets])
        if not self.enabled:
            return {}
        return {
            target.target_id: _SHORT_BODY
            for target in request.targets
            if target.field == "features[0].body"
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


def _feature_body(slide: dict[str, object], locale: str) -> str:
    payload = cast(dict[str, object], slide[f"presentation_{locale}"])
    return str(cast(list[dict[str, object]], payload["features"])[0]["body"])


@pytest.mark.unit
@pytest.mark.asyncio
class TestRevisionUsesViolations:
    async def test_revision_carries_violations_and_repairs_after(
        self, drafter: _Drafter
    ) -> None:
        """Scenario: A revision request carries the blocking violations."""
        repairer = _Repairer()
        engine = _engine(drafter, repairer)
        await park_at_content(engine)
        parked = await state_of(engine)
        assert parked["content_gate_validation"]["blocking"] is True
        assert repairer.rounds and "2:pt:features[0].body" in repairer.rounds[0]

        repairer.enabled = True
        await review(engine, Review(action=REVIEW_ACTION_REVISE, feedback=NOTE))

        notes = drafter.calls[-1]
        assert notes[0] == NOTE
        assert notes[1].startswith(GATE_REVISION_NOTE_HEADER)
        assert "- Slide 2 PT features[0].body: body_too_long" in notes[1]
        state = await state_of(engine)
        assert _feature_body(localized_slide(state, 2), "pt") == _SHORT_BODY
        history = feedback_history(state, PHASE_CONTENT)
        assert [(h["note"], h["status"]) for h in history] == [
            (NOTE, FEEDBACK_STATUS_APPLIED)
        ]

    async def test_revision_without_change_is_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A revision that changes nothing is not recorded as applied."""
        drafter = _Drafter(same=True)
        monkeypatch.setattr(GENERATE_TARGET, drafter)
        engine = _engine(drafter, _Repairer())
        await park_at_content(engine)

        await review(engine, Review(action=REVIEW_ACTION_REVISE, feedback=NOTE))

        state = await state_of(engine)
        assert state["content_gate_validation"]["blocking"] is True
        history = feedback_history(state, PHASE_CONTENT)
        assert [(h["note"], h["status"]) for h in history] == [
            (NOTE, FEEDBACK_STATUS_UNCHANGED)
        ]
