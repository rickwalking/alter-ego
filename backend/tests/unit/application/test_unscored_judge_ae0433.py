"""AE-0433: the judge retry on the next queue model and the stale-score re-score.

Fakes only (scripted judges, rewriters and scorers, ``FakeChat``); no
network, no real model.

Gherkin: tests/features/autopilot_unscored_judge_ae0433.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from langchain_core.language_models import BaseChatModel
from structlog.testing import capture_logs

from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
)
from rag_backend.application.services.carousel.persona_judge import judge_voice
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.slide_fix_loop import (
    LoopContext,
    fix_slide,
)
from rag_backend.application.services.carousel.slide_fix_service import fix_patch
from rag_backend.application.services.carousel.slide_fix_targets import (
    TargetQuery,
    select_targets,
    slide_issues,
    unscored_ticks,
)
from rag_backend.application.services.carousel.slide_fix_types import (
    DeckContext,
    SlideFixResult,
    SlideFixSettings,
    SlideFixTools,
    SlideIssue,
    SlideTarget,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.editorial.infrastructure.carousel_slide_fix import (
    _fallback_judge,
    _fallback_llm,
    _PersonaScorer,
)
from tests.unit.application.copy_hygiene_fixtures_ae0401 import POV, prod_deck, pt
from tests.unit.llm_fakes_ae0391 import FakeChat

SLIDE = 4
TEXT = "Eu testo o agente antes de abrir o PR."
EMOJI_BODY = "Escopo aberto 🚀 custa caro em toda revisão de PR."
CLEAN_BODY = "Escopo aberto custa caro em toda revisão de PR que eu faço."
CLEAN = json.dumps({"pt": {"body": CLEAN_BODY}}, ensure_ascii=False)
VOICE = SlideIssue(code="voice_score_low", message="Voice match score 55 is under 70")


@dataclass
class _Judge:
    answers: list[dict[str, object] | Exception]
    calls: list[str] = field(default_factory=list)

    async def evaluate_match(self, content: str) -> dict[str, object]:
        self.calls.append(content)
        answer = self.answers[min(len(self.calls), len(self.answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


@dataclass
class _Rewriter:
    answers: list[str]
    prompts: list[str] = field(default_factory=list)

    async def rewrite(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answers[min(len(self.prompts), len(self.answers)) - 1]


@dataclass
class _Scorer:
    scores: list[float | Exception | None]
    texts: list[str] = field(default_factory=list)

    async def score(self, text: str) -> float | None:
        self.texts.append(text)
        answer = self.scores[min(len(self.texts), len(self.scores)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


class _QueueChat(FakeChat):
    fallback: FakeChat | None = None

    def as_fallback(self) -> BaseChatModel | None:
        return self.fallback


@pytest.mark.unit
@pytest.mark.asyncio
class TestJudgeFallback:
    async def test_the_retry_goes_to_the_next_model_of_the_queue(self) -> None:
        """Scenario: A judge timeout on the first model is retried on the next model."""
        first = _Judge([TimeoutError()])
        second = _Judge([{"overall": 82.0}])
        with capture_logs() as logs:
            result = await judge_voice(first, TEXT, second)
        assert result == {"overall": 82.0}
        assert first.calls == [TEXT]
        assert second.calls == [TEXT]
        failed = [log for log in logs if log["event"] == "persona_judge_failed"]
        assert [(f["attempt"], f["fallback"], f["unscored"]) for f in failed] == [
            (1, False, False)
        ]

    async def test_a_failing_fallback_is_unscored(self) -> None:
        first = _Judge([TimeoutError()])
        second = _Judge([RuntimeError("down")])
        with capture_logs() as logs:
            assert await judge_voice(first, TEXT, second) is None
        failed = [log for log in logs if log["event"] == "persona_judge_failed"]
        assert [(f["fallback"], f["unscored"]) for f in failed] == [
            (False, False),
            (True, True),
        ]
        assert len(first.calls) == 1

    async def test_without_a_fallback_the_retry_stays_on_the_judge(self) -> None:
        judge = _Judge([TimeoutError(), {"overall": 75.0}])
        assert await judge_voice(judge, TEXT) == {"overall": 75.0}
        assert len(judge.calls) == 2

    async def test_the_scorer_retries_on_its_fallback_judge(self) -> None:
        scorer = _PersonaScorer(_Judge([TimeoutError()]), _Judge([{"overall": 8.2}]))
        assert await scorer.score(TEXT) == 82.0


@pytest.mark.unit
class TestFallbackModel:
    def test_a_queue_model_hands_its_next_model(self) -> None:
        nxt = FakeChat(model_name="next")
        assert _fallback_llm(_QueueChat(fallback=nxt)) is nxt

    def test_a_plain_model_has_no_fallback(self) -> None:
        assert _fallback_llm(FakeChat()) is None
        assert _fallback_judge(PersonaProfile(name="Pedro"), FakeChat()) is None

    def test_the_fallback_judge_is_the_persona_on_the_next_model(self) -> None:
        nxt = FakeChat(model_name="next")
        judge = _fallback_judge(PersonaProfile(name="Pedro"), _QueueChat(fallback=nxt))
        assert isinstance(judge, PersonaAgent)
        assert judge.llm is nxt

    def test_the_end_of_the_queue_has_no_fallback_judge(self) -> None:
        judge = _fallback_judge(PersonaProfile(name="Pedro"), _QueueChat(fallback=None))
        assert judge is None


def _deck(body: str | None = None) -> list[dict[str, object]]:
    deck = prod_deck()
    if body is not None:
        pt(deck, SLIDE)["body"] = body
    return deck


def _context(
    deck: list[dict[str, object]], rewriter: _Rewriter, scorer: _Scorer | None
) -> LoopContext:
    return LoopContext(
        deck=DeckContext(
            records=deck,
            policy_version=POV,
            autofix=AutofixContext(policy=load_presentation_policy(POV)),
            scored=True,
        ),
        tools=SlideFixTools(rewriter=rewriter, scorer=scorer),
        settings=SlideFixSettings(escalation_attempts=0),
    )


def _pending(deck: list[dict[str, object]], ticks: int = 1) -> SlideTarget:
    rules = slide_issues(deck, POV).get(SLIDE, [])
    return SlideTarget(
        slide_index=SLIDE,
        record=deck[SLIDE - 1],
        issues=(*rules, VOICE),
        score=55.0,
        unscored_ticks=ticks,
    )


@dataclass(frozen=True)
class _Case:
    scores: list[float | Exception | None]
    body: str | None = None
    ticks: int = 1
    answers: tuple[str, ...] = (CLEAN,)
    no_scorer: bool = False


async def _fix(case: _Case) -> tuple[SlideFixResult, _Rewriter, _Scorer]:
    deck = _deck(case.body)
    rewriter = _Rewriter(list(case.answers))
    scorer = _Scorer(case.scores)
    context = _context(deck, rewriter, None if case.no_scorer else scorer)
    return await fix_slide(_pending(deck, case.ticks), context), rewriter, scorer


@pytest.mark.unit
@pytest.mark.asyncio
class TestRescoreStale:
    async def test_a_passing_rescore_fixes_without_a_rewrite(self) -> None:
        """Scenario: A pending slide is re-scored on the next tick without a rewrite."""
        result, rewriter, scorer = await _fix(_Case(scores=[80.0]))
        assert result.fixed
        assert (result.score, result.unscored_ticks, result.attempts) == (80.0, 0, ())
        assert rewriter.prompts == []
        assert len(scorer.texts) == 1

    async def test_a_low_rescore_goes_back_to_the_rewrite_loop(self) -> None:
        """Scenario: A re-score that is still low goes back to the rewrite loop."""
        result, rewriter, scorer = await _fix(_Case(scores=[50.0, 85.0]))
        assert result.fixed
        assert (result.score, result.unscored_ticks) == (85.0, 0)
        assert "Voice match score 50 is under 70" in rewriter.prompts[0]
        assert scorer.texts[1] == CLEAN_BODY
        assert pt([result.record], 1)["body"] == CLEAN_BODY

    async def test_no_score_again_counts_one_more_tick(self) -> None:
        result, rewriter, _ = await _fix(_Case(scores=[None], ticks=2))
        assert result.fixed
        assert (result.score, result.unscored_ticks) == (55.0, 3)
        assert rewriter.prompts == []

    async def test_a_raising_scorer_is_no_score(self) -> None:
        result, _, _ = await _fix(_Case(scores=[RuntimeError("down")]))
        assert (result.fixed, result.unscored_ticks) == (True, 2)

    async def test_no_scorer_is_no_score(self) -> None:
        result, _, scorer = await _fix(_Case(scores=[80.0], no_scorer=True))
        assert (result.fixed, result.unscored_ticks) == (True, 2)
        assert scorer.texts == []

    async def test_rules_still_rewrite_and_a_judged_rewrite_clears_the_mark(
        self,
    ) -> None:
        result, rewriter, _ = await _fix(_Case(scores=[None, 90.0], body=EMOJI_BODY))
        assert result.fixed
        assert (result.score, result.unscored_ticks) == (90.0, 0)
        assert "visible_emoji_forbidden" in rewriter.prompts[0]
        assert "voice_score_low" not in rewriter.prompts[0]

    async def test_an_unjudged_rewrite_counts_one_tick_only(self) -> None:
        result, _, _ = await _fix(_Case(scores=[None], body=EMOJI_BODY))
        assert result.fixed
        assert (result.score, result.unscored_ticks) == (55.0, 2)

    async def test_an_unchanged_copy_with_a_stale_score_stays_unjudged(
        self,
    ) -> None:
        unchanged = json.dumps({"pt": {"body": EMOJI_BODY}}, ensure_ascii=False)
        result, _, scorer = await _fix(
            _Case(scores=[None], body=EMOJI_BODY, answers=(unchanged,))
        )
        assert not result.fixed
        assert result.unscored_ticks == 0
        assert len(scorer.texts) == 1

    async def test_a_fresh_unjudged_fix_starts_the_count(self) -> None:
        deck = _deck(EMOJI_BODY)
        rewriter = _Rewriter([CLEAN])
        target = SlideTarget(
            slide_index=SLIDE,
            record=deck[SLIDE - 1],
            issues=tuple(slide_issues(deck, POV)[SLIDE]),
            score=55.0,
        )
        result = await fix_slide(target, _context(deck, rewriter, _Scorer([None])))
        assert (result.fixed, result.score, result.unscored_ticks) == (True, 55.0, 1)


def _entries(**entries: object) -> dict[str, object]:
    return {"persona_scores": entries}


@pytest.mark.unit
class TestUnscoredTicks:
    def test_reads_only_pending_slide_entries(self) -> None:
        state = _entries(
            slide_1={"overall": 80},
            slide_2={"overall": 55, "rescore_pending": True, "unscored_ticks": 2},
            slide_3={"overall": 55, "rescore_pending": "yes", "unscored_ticks": 2},
            slide_4=55,
            slide_5={"overall": 55, "rescore_pending": True, "unscored_ticks": True},
            slide_6={"overall": 55, "rescore_pending": True},
            slide_7={"overall": 55, "rescore_pending": True, "unscored_ticks": 0},
            other={"rescore_pending": True, "unscored_ticks": 4},
        )
        assert unscored_ticks(state) == {2: 2, 5: 1, 6: 1, 7: 1}

    def test_no_scores_is_empty(self) -> None:
        assert unscored_ticks({}) == {}

    def test_a_pending_target_carries_its_ticks(self) -> None:
        deck = _deck()
        entries: dict[str, object] = {
            f"slide_{n}": {"overall": 80} for n in range(1, 10)
        }
        entries["slide_4"] = {
            "overall": 55,
            "rescore_pending": True,
            "unscored_ticks": 2,
        }
        state = _entries(**entries)
        selection = select_targets(
            TargetQuery(
                records=deck,
                state=state,
                policy_version=POV,
                phase=PHASE_CONTENT,
                voice_floor=70.0,
            )
        )
        assert [(t.slide_index, t.unscored_ticks) for t in selection.targets] == [
            (4, 2)
        ]


def _result(score: float | None = 55.0, unscored_ticks: int = 0) -> SlideFixResult:
    return SlideFixResult(
        slide_index=2,
        fixed=True,
        record={"slide_index": 2},
        issues=(),
        attempts=(),
        score=score,
        unscored_ticks=unscored_ticks,
    )


@pytest.mark.unit
class TestScoresPatch:
    def _patch(
        self, entry: object, result: SlideFixResult
    ) -> dict[str, object] | object:
        state: dict[str, object] = {
            "localized_slides": [],
            "persona_scores": {"slide_2": entry, "slide_3": 80},
        }
        scores = fix_patch(state, [result])["persona_scores"]
        assert isinstance(scores, dict)
        assert scores["slide_3"] == 80
        return scores["slide_2"]

    def test_an_unjudged_fix_keeps_the_score_and_marks_it(self) -> None:
        entry = self._patch(
            {"overall": 55.0, "tone_match": 5}, _result(unscored_ticks=1)
        )
        assert entry == {
            "overall": 55.0,
            "tone_match": 5,
            "rescore_pending": True,
            "unscored_ticks": 1,
        }

    def test_a_judged_fix_clears_the_mark(self) -> None:
        pending = {"overall": 55.0, "rescore_pending": True, "unscored_ticks": 2}
        assert self._patch(pending, _result(score=81.0)) == {"overall": 81.0}

    def test_a_bare_number_entry_is_marked(self) -> None:
        entry = self._patch(55, _result(unscored_ticks=1))
        assert entry == {"overall": 55.0, "rescore_pending": True, "unscored_ticks": 1}

    def test_no_score_keeps_the_entry(self) -> None:
        assert self._patch(55, _result(score=None)) == 55
