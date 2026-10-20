"""AE-0439: the content-generation scoring stores 0-100 entries (QA F-12) and
retries a timed-out judge on the queue's next model (#154 A).

Fakes only; no network.

Gherkin: tests/features/blog_carousel_minors_ae0439.feature
  - Scenario: Stored persona scores are on 0-100 even for a raw 0-10 judge answer
  - Scenario: The content-generation judge retries on the queue's next model
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models import BaseChatModel

import rag_backend.application.services.carousel.phase_artifact_runner as runner_module
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.domain.models.persona import PersonaProfile
from tests.unit.llm_fakes_ae0391 import FakeChat

TEXT = "Eu testo o agente antes de abrir o PR."
PERSONA = PersonaProfile(name="Pedro")


@dataclass
class _RawJudge:
    """``evaluate_match`` answers in order; an Exception entry is raised."""

    answers: list[dict[str, object] | Exception]
    calls: list[str] = field(default_factory=list)

    async def evaluate_match(self, content: str) -> dict[str, object]:
        self.calls.append(content)
        answer = self.answers[min(len(self.calls), len(self.answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


class _FallbackChat(FakeChat):
    """A fake chat model that hands a call to the next model of the queue."""

    fallback_model: FakeChat | None = None

    def as_fallback(self) -> BaseChatModel | None:
        return self.fallback_model


def _judge_factory(
    monkeypatch: pytest.MonkeyPatch,
    primary: _RawJudge,
    fallback: _RawJudge | None = None,
) -> None:
    """Every ``PersonaAgent(...)`` call returns the judge bound to its model."""

    def make(persona: PersonaProfile, llm: BaseChatModel) -> _RawJudge:
        del persona
        if getattr(llm, "model_name", "") == "fallback":
            assert fallback is not None
            return fallback
        return primary

    monkeypatch.setattr(runner_module, "PersonaAgent", make)


def _runner(llm: BaseChatModel) -> PhaseArtifactRunner:
    return PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(), content_agent=MagicMock(), llm=llm
        )
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestContentScoring:
    async def test_a_raw_ten_point_answer_is_stored_on_hundred(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Stored persona scores are on 0-100 for a raw 0-10 answer."""
        primary = _RawJudge(
            [{"tone_match": 9.0, "overall": 8.5, "suggestions": ["keep the contract"]}]
        )
        _judge_factory(monkeypatch, primary)
        scores = await _runner(_FallbackChat())._score_slides(
            [{"draft_text": TEXT}], PERSONA
        )
        assert set(scores) == {"slide_1"}
        entry = scores["slide_1"]
        assert isinstance(entry, dict)
        assert entry["overall"] == pytest.approx(85.0)
        assert entry["tone_match"] == pytest.approx(90.0)
        assert entry["suggestions"] == ["keep the contract"]

    async def test_a_timed_out_judge_is_retried_on_the_next_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The content-generation judge retries on the queue's next model."""
        primary = _RawJudge([asyncio.TimeoutError("slow")])
        fallback = _RawJudge([{"overall": 80.0}])
        _judge_factory(monkeypatch, primary, fallback)
        llm = _FallbackChat(
            model_name="primary", fallback_model=FakeChat(model_name="fallback")
        )
        scores = await _runner(llm)._score_slides([{"draft_text": TEXT}], PERSONA)
        assert scores["slide_1"] == {"overall": 80.0}
        assert primary.calls == [TEXT]
        assert fallback.calls == [TEXT]

    async def test_a_judge_without_a_fallback_stays_unscored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        primary = _RawJudge([RuntimeError("down"), RuntimeError("down")])
        _judge_factory(monkeypatch, primary)
        scores = await _runner(FakeChat(model_name="primary"))._score_slides(
            [{"draft_text": TEXT}], PERSONA
        )
        assert scores == {}
