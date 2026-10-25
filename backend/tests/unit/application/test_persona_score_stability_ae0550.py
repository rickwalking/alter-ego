"""The persona voice gate: stable scores, the visible copy, and hand edits that clear it.

Feature: backend/tests/features/persona_score_stability_ae0550.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import rag_backend.agents.carousel_workflow_nodes as nodes
import rag_backend.application.services.carousel.phase_artifact_runner as runner_module
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    validate_content_approve_persona_score,
)
from rag_backend.application.services.carousel.persona_slide_scoring import (
    VOICE_TEXT_FINGERPRINT_KEY,
    SlideVoiceScoring,
    reusable_score,
    score_slide_voices,
    text_fingerprint,
    voice_text,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.domain.models.persona import PersonaProfile
from tests.unit.llm_fakes_ae0391 import FakeChat

PERSONA = PersonaProfile(name="Pedro")


@dataclass
class _ScriptedJudge:
    """Scores by text; records every judged text."""

    by_text: dict[str, float]
    calls: list[str] = field(default_factory=list)

    async def evaluate_match(self, content: str) -> dict[str, object]:
        self.calls.append(content)
        return {"overall": self.by_text.get(content, 80.0), "suggestions": []}


def _slide(heading: str, body: str) -> dict[str, object]:
    return {"presentation_pt": {"heading": heading, "body": body}, "draft_text": body}


def _scored(slide: dict[str, object], overall: float) -> dict[str, object]:
    return {
        "overall": overall,
        VOICE_TEXT_FINGERPRINT_KEY: text_fingerprint(voice_text(slide)),
    }


async def _score(
    slides: list[object], judge: _ScriptedJudge, previous: object
) -> dict[str, object]:
    return await score_slide_voices(
        SlideVoiceScoring(
            slide_drafts=slides,
            judge=judge,
            fallback=None,
            previous=previous,
            concurrency=2,
        )
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestStability:
    async def test_unchanged_slides_keep_their_scores_without_a_judge_call(
        self,
    ) -> None:
        """Scenario: An unchanged slide keeps its score"""
        slides = [_slide("Um", "Eu testo antes."), _slide("Dois", "Sem pressa.")]
        first_judge = _ScriptedJudge({
            voice_text(slides[0]): 90.0,
            voice_text(slides[1]): 73.0,
        })
        first = await _score(slides, first_judge, None)
        again_judge = _ScriptedJudge({})
        again = await _score(slides, again_judge, first)
        assert again_judge.calls == []
        assert again == first
        assert [entry["overall"] for entry in again.values()] == [90.0, 73.0]

    async def test_only_the_changed_slide_is_judged(self) -> None:
        """Scenario: An unchanged slide keeps its score"""
        slides = [_slide("Um", "Eu testo antes."), _slide("Dois", "Sem pressa.")]
        previous = {
            "slide_1": _scored(slides[0], 90.0),
            "slide_2": _scored(slides[1], 62.0),
        }
        edited = [
            slides[0],
            _slide("Dois", "Eu vou direto: teste antes de abrir o PR."),
        ]
        judge = _ScriptedJudge({voice_text(edited[1]): 84.0})
        scores = await _score(edited, judge, previous)
        assert judge.calls == [voice_text(edited[1])]
        assert scores["slide_1"] == previous["slide_1"]
        assert scores["slide_2"]["overall"] == 84.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_an_edit_that_improves_the_voice_clears_the_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: An edit that improves the voice clears the gate"""
    before = [_slide("Um", "Eu testo antes."), _slide("Dois", "Texto genérico.")]
    after = [before[0], _slide("Dois", "Eu vou direto: teste antes de abrir o PR.")]
    state: dict[str, object] = {
        "current_phase": "content",
        "slide_drafts": after,
        "persona_scores": {
            "slide_1": _scored(before[0], 90.0),
            "slide_2": _scored(before[1], 62.0),
        },
    }
    with pytest.raises(ValueError, match="persona_score_too_low"):
        validate_content_approve_persona_score({**state})
    judge = _ScriptedJudge({voice_text(after[1]): 85.0})
    monkeypatch.setattr(runner_module, "PersonaAgent", lambda persona, llm: judge)
    monkeypatch.setattr(
        runner_module,
        "resolve_workflow_input",
        lambda state, workflow_input: SimpleNamespace(persona=PERSONA),
    )
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=FakeChat(model_name="primary"),
            workflow_input=MagicMock(),
        )
    )
    updates = await runner.rescore_edited_content(state)
    scores = updates["persona_scores"]
    assert judge.calls == [voice_text(after[1])]
    assert scores["slide_1"]["overall"] == 90.0
    assert scores["slide_2"]["overall"] == 85.0
    validate_content_approve_persona_score({**state, **updates})


@pytest.mark.unit
def test_the_judge_reads_the_visible_copy() -> None:
    """Scenario: The judge reads the slide's visible copy"""
    slide = {
        "presentation_pt": {
            "heading": "Três passos",
            "body": "Comece pequeno.",
            "summary_points": [
                {"title": "Teste", "body": "Rode no seu repo."},
                {"title": "Leia", "body": ""},
                {"title": "", "body": "Peça ajuda."},
            ],
        },
        "draft_text": "Comece pequeno.",
    }
    assert voice_text(slide) == (
        "Três passos\nComece pequeno.\nTeste: Rode no seu repo.\nLeia\nPeça ajuda."
    )
    assert voice_text({"title": "Título", "draft_text": "Corpo."}) == "Título\nCorpo."


@pytest.mark.unit
def test_a_stale_or_unscored_entry_is_judged_again() -> None:
    """Scenario: A stale or unscored entry is judged again"""
    fingerprint = text_fingerprint("texto")
    valid = {"overall": 80.0, VOICE_TEXT_FINGERPRINT_KEY: fingerprint}
    assert reusable_score({"slide_1": valid}, "slide_1", fingerprint) == valid
    assert (
        reusable_score({"slide_1": valid}, "slide_1", text_fingerprint("outro")) is None
    )
    assert (
        reusable_score({"slide_1": {"overall": 80.0}}, "slide_1", fingerprint) is None
    )
    pending = {**valid, "rescore_pending": True}
    assert reusable_score({"slide_1": pending}, "slide_1", fingerprint) is None
    unscored = {"overall": 0.0, VOICE_TEXT_FINGERPRINT_KEY: fingerprint}
    assert reusable_score({"slide_1": unscored}, "slide_1", fingerprint) is None
    assert reusable_score(None, "slide_1", fingerprint) is None


@dataclass
class _ReplayRunner:
    rescored: list[dict[str, object]] = field(default_factory=list)

    async def rescore_edited_content(
        self, state: dict[str, object]
    ) -> dict[str, object]:
        self.rescored.append(state)
        return {"persona_scores": {"slide_2": {"overall": 85.0}}}

    async def ensure_for_phase(self, state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("the parked replay must not regenerate")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_the_parked_replay_rescores_instead_of_regenerating() -> None:
    """Scenario: An edit that improves the voice clears the gate"""
    runner = _ReplayRunner()
    state = {"project_id": "p1", "content_artifacts_parked": True}
    config = {"configurable": {"artifact_runner": runner}}
    updates = await nodes._content_ensure_or_reuse(state, config)
    assert updates == {"persona_scores": {"slide_2": {"overall": 85.0}}}
    assert runner.rescored == [state]
    assert await nodes._content_ensure_or_reuse(state, None) == {}
