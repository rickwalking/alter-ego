"""The slide fix escalates to the reasoning model, and the judge.

Fakes only: the rewriters and the scorer are scripted, no model is built.

Gherkin: tests/features/autofix_escalation_ae0407.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.slide_fix_loop import (
    LoopContext,
    fix_slide,
)
from rag_backend.application.services.carousel.slide_fix_service import fix_patch
from rag_backend.application.services.carousel.slide_fix_targets import slide_issues
from rag_backend.application.services.carousel.slide_fix_types import (
    DeckContext,
    SlideFixResult,
    SlideFixSettings,
    SlideFixTools,
    SlideTarget,
)
from tests.unit.application.copy_hygiene_fixtures_ae0401 import POV, prod_deck, pt

SLIDE = 4
EMOJI_BODY = "Escopo aberto 🚀 custa caro em toda revisão de PR."
CLEAN_BODY = "Escopo aberto custa caro em toda revisão de PR que eu faço."
FAST = "fast"
REASONING = "reasoning"


def _answer(body: str) -> str:
    return json.dumps({"pt": {"body": body}}, ensure_ascii=False)


EMOJI = _answer(EMOJI_BODY)
CLEAN = _answer(CLEAN_BODY)


@dataclass
class _Rewriter:
    """Answers in order (the last repeats); an Exception entry is raised."""

    answers: list[str | Exception]
    prompts: list[str] = field(default_factory=list)

    async def rewrite(self, prompt: str) -> str:
        self.prompts.append(prompt)
        answer = self.answers[min(len(self.prompts), len(self.answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


@dataclass
class _Scorer:
    scores: list[float | None]
    texts: list[str] = field(default_factory=list)

    async def score(self, text: str) -> float | None:
        self.texts.append(text)
        return self.scores[min(len(self.texts), len(self.scores)) - 1]


def _deck() -> list[dict[str, object]]:
    deck = prod_deck()
    pt(deck, SLIDE)["body"] = EMOJI_BODY
    return deck


def _target(deck: list[dict[str, object]], score: float | None = None) -> SlideTarget:
    issues = slide_issues(deck, POV).get(SLIDE, [])
    return SlideTarget(
        slide_index=SLIDE, record=deck[SLIDE - 1], issues=tuple(issues), score=score
    )


@dataclass(frozen=True)
class _Run:
    fast: _Rewriter
    reasoning: _Rewriter | None = None
    escalation_attempts: int = 2
    scorer: _Scorer | None = None
    target_score: float | None = None


async def _fix(run: _Run) -> SlideFixResult:
    deck = _deck()
    context = LoopContext(
        deck=DeckContext(
            records=deck,
            policy_version=POV,
            autofix=AutofixContext(policy=load_presentation_policy(POV)),
            scored=run.scorer is not None,
        ),
        tools=SlideFixTools(
            rewriter=run.fast,
            scorer=run.scorer,
            escalation_rewriter=run.reasoning,
        ),
        settings=SlideFixSettings(escalation_attempts=run.escalation_attempts),
    )
    return await fix_slide(_target(deck, run.target_score), context)


def _trail(result: SlideFixResult) -> list[tuple[int, str, str]]:
    return [(a.attempt, a.model_role, a.outcome) for a in result.attempts]


@pytest.mark.unit
@pytest.mark.asyncio
class TestEscalation:
    """Item 1: the reasoning model after 3 failed fast attempts."""

    async def test_the_seeded_slide_fails_on_the_emoji(self) -> None:
        codes = [issue.code for issue in _target(_deck()).issues]
        assert codes == ["visible_emoji_forbidden"]

    async def test_fixed_on_attempt_2_by_the_fast_model(self) -> None:
        """Scenario: Fixed on attempt 2 by the fast model."""
        reasoning = _Rewriter([CLEAN])
        result = await _fix(_Run(fast=_Rewriter([EMOJI, CLEAN]), reasoning=reasoning))
        assert result.fixed
        assert _trail(result) == [(1, FAST, "still_failing"), (2, FAST, "fixed")]
        assert reasoning.prompts == []
        assert pt([result.record], 1)["body"] == CLEAN_BODY

    async def test_fixed_on_attempt_4_by_the_reasoning_model(self) -> None:
        """Scenario: Fixed on attempt 4 by the reasoning model.

        The reasoning model starts from the last copy and its failing check.
        """
        fast = _Rewriter([EMOJI])
        reasoning = _Rewriter([CLEAN])
        result = await _fix(_Run(fast=fast, reasoning=reasoning))
        assert result.fixed
        assert _trail(result) == [
            (1, FAST, "still_failing"),
            (2, FAST, "still_failing"),
            (3, FAST, "still_failing"),
            (4, REASONING, "fixed"),
        ]
        assert len(fast.prompts) == 3
        assert "visible_emoji_forbidden" in reasoning.prompts[0]
        assert result.issues == ()

    async def test_still_failing_after_5_attempts(self) -> None:
        """Scenario: Still failing after 5 attempts escalates with every attempt counted."""
        reasoning = _Rewriter([EMOJI])
        result = await _fix(_Run(fast=_Rewriter([EMOJI]), reasoning=reasoning))
        assert not result.fixed
        assert [a.attempt for a in result.attempts] == [1, 2, 3, 4, 5]
        assert [a.model_role for a in result.attempts] == [FAST] * 3 + [REASONING] * 2
        assert len(reasoning.prompts) == 2
        assert [i.code for i in result.issues] == ["visible_emoji_forbidden"]
        assert pt([result.record], 1)["body"] == EMOJI_BODY

    async def test_escalation_attempts_0_stops_after_3(self) -> None:
        """Scenario: Escalation attempts 0 escalates after 3 attempts."""
        reasoning = _Rewriter([CLEAN])
        run = _Run(fast=_Rewriter([EMOJI]), reasoning=reasoning, escalation_attempts=0)
        result = await _fix(run)
        assert not result.fixed
        assert len(result.attempts) == 3
        assert reasoning.prompts == []

    async def test_no_reasoning_model_stops_after_3(self) -> None:
        result = await _fix(_Run(fast=_Rewriter([EMOJI])))
        assert [a.model_role for a in result.attempts] == [FAST] * 3

    async def test_a_reasoning_model_error_counts_as_an_attempt(self) -> None:
        """Scenario: A reasoning-model error counts as an attempt."""
        reasoning = _Rewriter([RuntimeError("provider down"), CLEAN])
        result = await _fix(_Run(fast=_Rewriter([EMOJI]), reasoning=reasoning))
        assert result.fixed
        assert _trail(result)[3:] == [
            (4, REASONING, "model_error"),
            (5, REASONING, "fixed"),
        ]
        assert "The previous attempt failed: RuntimeError" in reasoning.prompts[1]


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnscoredJudge:
    """Item 3: a judge with no score keeps the previous score, no voice issue."""

    async def test_unscored_rewrite_keeps_the_previous_score(self) -> None:
        """Scenario: A judge that fails twice leaves the slide unscored.

        The kept score is marked for a re-score on the next tick.
        """
        scorer = _Scorer([None])
        run = _Run(fast=_Rewriter([CLEAN]), scorer=scorer, target_score=50.0)
        result = await _fix(run)
        assert result.fixed
        assert result.score == 50.0
        assert scorer.texts == [CLEAN_BODY]
        patch = fix_patch({"persona_scores": {"slide_4": {"overall": 50.0}}}, [result])
        assert patch["persona_scores"] == {
            "slide_4": {"overall": 50.0, "rescore_pending": True, "unscored_ticks": 1}
        }

    async def test_a_low_judged_score_is_still_a_voice_issue(self) -> None:
        """An unfixed slide keeps the target's score."""
        run = _Run(
            fast=_Rewriter([CLEAN]), scorer=_Scorer([40.0]), escalation_attempts=0
        )
        result = await _fix(run)
        assert not result.fixed
        assert [i.code for i in result.issues] == ["voice_score_low"]
        assert result.score is None

    async def test_a_good_judged_score_is_stored(self) -> None:
        result = await _fix(
            _Run(fast=_Rewriter([CLEAN]), scorer=_Scorer([82.0]), target_score=50.0)
        )
        assert result.fixed
        assert result.score == 82.0

    async def test_unscored_slide_without_a_previous_score_writes_none(self) -> None:
        result = await _fix(_Run(fast=_Rewriter([CLEAN]), scorer=_Scorer([None])))
        assert result.fixed
        assert result.score is None
        patch = fix_patch({"persona_scores": {"slide_2": {"overall": 80.0}}}, [result])
        assert patch["persona_scores"] == {"slide_2": {"overall": 80.0}}
