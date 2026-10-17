"""AE-0407: a failed persona judge call is retried once and never a verdict.

Fakes only (scripted judges, ``FakeChat``); no network, no real model.

Gherkin: tests/features/autofix_escalation_ae0407.feature (item 2 parse
scenario and the item 3 scenarios).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest
from structlog.testing import capture_logs

from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.application.services.carousel import persona_judge
from rag_backend.application.services.carousel.persona_judge import judge_voice
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.editorial.infrastructure.carousel_slide_fix import (
    _PersonaScorer,
)
from tests.unit.llm_fakes_ae0391 import FakeChat

TEXT = "Eu testo o agente antes de abrir o PR."
FAILED = "persona_judge_failed"


@dataclass
class _Judge:
    """``evaluate_match`` answers in order; an Exception entry is raised."""

    answers: list[dict[str, object] | Exception]
    calls: list[str] = field(default_factory=list)
    delay: float = 0.0

    async def evaluate_match(self, content: str) -> dict[str, object]:
        self.calls.append(content)
        if self.delay:
            await asyncio.sleep(self.delay)
        answer = self.answers[min(len(self.calls), len(self.answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


def _failed(logs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [log for log in logs if log["event"] == FAILED]


@pytest.mark.unit
@pytest.mark.asyncio
class TestJudgeVoice:
    async def test_a_good_first_answer_is_one_call(self) -> None:
        judge = _Judge([{"overall": 81.0}])
        assert await judge_voice(judge, TEXT) == {"overall": 81.0}
        assert judge.calls == [TEXT]

    async def test_a_zero_is_retried_once(self) -> None:
        """Scenario: A judge call that parses to 0.0 is retried once."""
        judge = _Judge([{"overall": 0.0}, {"overall": 82.0}])
        with capture_logs() as logs:
            result = await judge_voice(judge, TEXT)
        assert result == {"overall": 82.0}
        assert len(judge.calls) == 2
        assert [(f["attempt"], f["reason"], f["unscored"]) for f in _failed(logs)] == [
            (1, "no_score", False)
        ]

    async def test_two_failures_are_unscored(self) -> None:
        """Scenario: A judge that fails twice leaves the slide unscored."""
        judge = _Judge([RuntimeError("down"), {"tone_match": 80.0}])
        with capture_logs() as logs:
            result = await judge_voice(judge, TEXT)
        assert result is None
        assert [(f["attempt"], f["reason"], f["unscored"]) for f in _failed(logs)] == [
            (1, "error:RuntimeError", False),
            (2, "no_score", True),
        ]

    async def test_a_timeout_is_a_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A judge timeout is a failure, not a verdict."""
        monkeypatch.setattr(persona_judge, "PERSONA_JUDGE_TIMEOUT_SECONDS", 0.01)
        judge = _Judge([{"overall": 90.0}], delay=1.0)
        with capture_logs() as logs:
            assert await judge_voice(judge, TEXT) is None
        assert [f["reason"] for f in _failed(logs)] == ["error:TimeoutError"] * 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestPersonaScorer:
    async def test_scorer_reads_the_judged_overall(self) -> None:
        agent = _Judge([{"overall": 7.8}])
        scorer = _PersonaScorer(agent)
        assert await scorer.score(TEXT) == 78.0

    async def test_scorer_returns_none_when_unscored(self) -> None:
        scorer = _PersonaScorer(_Judge([{"overall": 0.0}]))
        assert await scorer.score(TEXT) is None


def _parse(answer: dict[str, float]) -> dict[str, object]:
    agent = PersonaAgent(persona=PersonaProfile(name="Pedro"), llm=FakeChat())
    return agent._parse_evaluation_response(json.dumps(answer))


@pytest.mark.unit
class TestParseScale:
    def test_overall_on_ten_is_scaled_with_a_sub_score_on_hundred(self) -> None:
        """Scenario: The judge's overall on 0-10 is scaled even when a sub-score is on 0-100."""
        scores = _parse({"tone_match": 78.0, "originality": 6.0, "overall": 7.8})
        assert scores["overall"] == pytest.approx(78.0)
        assert scores["tone_match"] == 78.0
        assert scores["originality"] == 6.0

    def test_an_all_ten_point_answer_is_scaled_once(self) -> None:
        scores = _parse({"tone_match": 8.0, "overall": 8.5})
        assert scores["overall"] == pytest.approx(85.0)
        assert scores["tone_match"] == pytest.approx(80.0)

    def test_a_hundred_point_overall_is_kept(self) -> None:
        assert _parse({"tone_match": 9.0, "overall": 78.0})["overall"] == 78.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_the_content_phase_omits_an_unscored_slide() -> None:
    """Scenario: The content phase omits an unscored slide."""
    good = json.dumps({"overall": 80})

    def reply(prompt: str) -> str:
        return "not json" if "slide two copy" in prompt.lower() else good

    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=FakeChat(reply=reply),
        )
    )
    drafts: list[object] = [
        {"draft_text": "Slide one copy"},
        {"draft_text": "Slide two copy"},
        {"draft_text": "Slide three copy"},
    ]
    with capture_logs() as logs:
        scores = await runner._score_slides(drafts, PersonaProfile(name="Pedro"))
    assert set(scores) == {"slide_1", "slide_3"}
    assert scores["slide_1"] == {
        **dict.fromkeys(_SUB_FIELDS, 0.0),
        "overall": 80.0,
        "suggestions": [],
    }
    assert len(_failed(logs)) == 2


_SUB_FIELDS = (
    "tone_match",
    "sentence_structure_match",
    "opinion_strength",
    "originality",
    "human_authenticity",
)
