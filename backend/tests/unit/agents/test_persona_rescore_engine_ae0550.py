"""Submit manual fixes re-scores the edited slide in the persisted workflow state.

Real ``CarouselWorkflowEngine`` (in-memory checkpointer) and real
``PhaseArtifactRunner`` (the ``content_feedback_flow_ae0405`` harness); only the
drafting model and the persona judge are fakes.

Gherkin: tests/features/persona_score_stability_ae0550.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

import rag_backend.application.services.carousel.phase_artifact_runner as runner_module
from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    validate_content_approve_persona_score,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    content_approve_blocker,
)
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    DraftingModel,
    edited_slide,
    manual_fixes,
    park_at_content,
    review,
    state_of,
)

_EDITED_MARK = "corrigido"
_WEAK_MARK = "insight 3"
_LOW, _HIGH, _EDITED = 62.0, 90.0, 88.0


@dataclass
class _Judge:
    """The persona judge: slide 3's draft is off-voice, the hand fix is on it."""

    calls: list[str] = field(default_factory=list)

    @staticmethod
    def style_guide() -> str:
        return ""

    async def evaluate_match(self, content: str) -> dict[str, object]:
        self.calls.append(content)
        if _EDITED_MARK in content:
            return {"overall": _EDITED, "suggestions": []}
        return {"overall": _LOW if _WEAK_MARK in content else _HIGH, "suggestions": []}


@pytest.fixture
def judge(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Judge]:
    spy = _Judge()
    monkeypatch.setattr(GENERATE_TARGET, DraftingModel())
    monkeypatch.setattr(runner_module, "PersonaAgent", lambda persona, llm: spy)
    yield spy


def _engine() -> CarouselWorkflowEngine:
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            workflow_input=EditorialWorkflowStartInput(
                topic="Agentes",
                audience="devs",
                brief="b",
                sources=[],
                persona=PersonaProfile(name="Pedro"),
            ),
        )
    )
    return CarouselWorkflowEngine(checkpointer=InMemorySaver(), artifact_runner=runner)


def _overall(state: dict[str, object], key: str) -> object:
    scores = state["persona_scores"]
    assert isinstance(scores, dict)
    entry = scores[key]
    assert isinstance(entry, dict)
    return entry["overall"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_manual_fixes_persists_the_new_score_and_clears_the_gate(
    judge: _Judge,
) -> None:
    """Scenario: An edit that improves the voice clears the gate"""
    engine = _engine()
    await park_at_content(engine)
    before = await state_of(engine)
    assert _overall(before, "slide_3") == _LOW
    assert content_approve_blocker(before) == "persona_score_too_low"
    first_calls = len(judge.calls)

    await review(engine, manual_fixes(edited_slide(before, 3)))

    after = await state_of(engine)
    assert _overall(after, "slide_3") == _EDITED
    assert after["persona_scores"]["slide_1"] == before["persona_scores"]["slide_1"]
    assert len(judge.calls) == first_calls + 1
    assert _EDITED_MARK in judge.calls[-1]
    validate_content_approve_persona_score(after)
    assert content_approve_blocker(after) != "persona_score_too_low"
