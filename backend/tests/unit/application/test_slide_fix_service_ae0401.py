"""AE-0401: the slide-fix service, its targets, prompt and answer parsing.

Gherkin: tests/features/autopilot_slide_autofix_ae0401.feature
(scenario "A low voice score on one slide is rewritten and re-scored") and
the edges the runner flow does not reach.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.slide_fix_loop import (
    LoopContext,
    current_text,
    fix_slide,
)
from rag_backend.application.services.carousel.slide_fix_prompt import (
    apply_answer,
    issue_lines,
    render_slide_fix_prompt,
)
from rag_backend.application.services.carousel.slide_fix_service import (
    SlideFixDeps,
    SlideFixService,
    fix_patch,
)
from rag_backend.application.services.carousel.slide_fix_targets import (
    TargetQuery,
    overall_score,
    select_targets,
    slide_scores,
)
from rag_backend.application.services.carousel.slide_fix_types import (
    DeckContext,
    SlideFixCommand,
    SlideFixResult,
    SlideFixSettings,
    SlideFixTools,
    SlideIssue,
    SlideTarget,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_FIXED,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT, PHASE_DESIGN
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.modules.autopilot.domain.gate import GateAction
from rag_backend.modules.autopilot.domain.policy import decide
from tests.unit.application.content_gate_fixtures_ae0392 import (
    GateSeed,
    RealGate,
    seed_gate,
)
from tests.unit.application.copy_hygiene_fixtures_ae0401 import (
    POV,
    en,
    prod_deck,
    pt,
)
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    LOCK_VERSION,
    FakeChatModel,
    build_engine,
)

REWRITTEN_2 = "O Argon resume o relatório em três números que eu confiro sempre."


@dataclass
class _Rewriter:
    answers: list[str]
    prompts: list[str] = field(default_factory=list)

    async def rewrite(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answers[min(len(self.prompts), len(self.answers)) - 1]


@dataclass
class _Scorer:
    score_value: float
    texts: list[str] = field(default_factory=list)

    async def score(self, text: str) -> float:
        self.texts.append(text)
        return self.score_value


def _answer(**pt_copy: object) -> str:
    return json.dumps({"pt": pt_copy}, ensure_ascii=False)


@pytest.mark.unit
@pytest.mark.asyncio
class TestVoiceScoreFix:
    """Scenario: A low voice score on one slide is rewritten and re-scored."""

    async def test_low_voice_slide_is_rewritten_and_rescored(
        self, db_session: AsyncSession
    ) -> None:
        engine = build_engine(FakeChatModel())
        project_id = await seed_gate(engine, db_session, GateSeed())
        scores = {f"slide_{n}": {"overall": 80.0, "tone_match": 8} for n in range(1, 8)}
        scores["slide_2"] = {"overall": 50.0, "tone_match": 5}
        await engine.update_workflow_state(project_id, {"persona_scores": scores})
        rewriter = _Rewriter([_answer(body=REWRITTEN_2)])
        scorer = _Scorer(85.0)
        service = SlideFixService(
            SlideFixDeps(
                db=db_session,
                repo=PostgresCarouselRepository(session=db_session),
                workflow=engine,
                tools=SlideFixTools(rewriter=rewriter, scorer=scorer, style_guide="G"),
                settings=SlideFixSettings(concurrency=2),
            )
        )
        outcome = await service.fix(
            SlideFixCommand(
                project_id=project_id,
                expected_version=LOCK_VERSION,
                phase=PHASE_CONTENT,
            )
        )
        assert outcome.status == AUTOFIX_STATUS_FIXED
        assert [r.slide_index for r in outcome.results] == [2]
        assert "voice_score_low" in rewriter.prompts[0]
        assert "G" in rewriter.prompts[0]
        assert scorer.texts == [REWRITTEN_2]
        state = await engine.get_workflow_state(project_id)
        assert state is not None
        stored = cast(dict[str, dict[str, object]], state["persona_scores"])
        assert stored["slide_2"] == {"overall": 85.0, "tone_match": 5}
        assert stored["slide_3"]["overall"] == 80.0
        slides = cast(list[dict[str, dict[str, object]]], state["localized_slides"])
        assert slides[1]["presentation_pt"]["body"] == REWRITTEN_2
        snapshot = await RealGate(db=db_session, engine=engine).read_gate(project_id)
        assert decide(snapshot).action is GateAction.APPROVE

    async def test_voice_is_ignored_at_the_design_gate(
        self, db_session: AsyncSession
    ) -> None:
        engine = build_engine(FakeChatModel())
        project_id = await seed_gate(engine, db_session, GateSeed(phase=PHASE_DESIGN))
        await engine.update_workflow_state(
            project_id, {"persona_scores": {"slide_2": {"overall": 10.0}}}
        )
        rewriter = _Rewriter([_answer(body=REWRITTEN_2)])
        service = SlideFixService(
            SlideFixDeps(
                db=db_session,
                repo=PostgresCarouselRepository(session=db_session),
                workflow=engine,
                tools=SlideFixTools(rewriter=rewriter),
                settings=SlideFixSettings(),
            )
        )
        outcome = await service.fix(
            SlideFixCommand(
                project_id=project_id, expected_version=LOCK_VERSION, phase=PHASE_DESIGN
            )
        )
        assert outcome.status == AUTOFIX_STATUS_NOTHING_TO_FIX
        assert rewriter.prompts == []

    async def test_no_checkpoint_is_nothing_to_fix(
        self, db_session: AsyncSession
    ) -> None:
        service = SlideFixService(
            SlideFixDeps(
                db=db_session,
                repo=PostgresCarouselRepository(session=db_session),
                workflow=None,
                tools=SlideFixTools(rewriter=_Rewriter([""])),
                settings=SlideFixSettings(),
            )
        )
        outcome = await service.fix(
            SlideFixCommand(
                project_id="00000000-0000-4000-a000-000000000000",
                expected_version=1,
                phase=PHASE_CONTENT,
            )
        )
        assert outcome.status == AUTOFIX_STATUS_NOTHING_TO_FIX


def _deck_context(deck: list[dict[str, object]], *, scored: bool) -> DeckContext:
    return DeckContext(
        records=deck,
        policy_version=POV,
        autofix=AutofixContext(policy=load_presentation_policy(POV)),
        scored=scored,
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestLoopEdges:
    async def test_unchanged_copy_keeps_the_score(self) -> None:
        deck = prod_deck()
        target = SlideTarget(
            slide_index=4,
            record=deck[3],
            issues=(SlideIssue(code="voice_score_low", message="low"),),
            score=40.0,
        )
        scorer = _Scorer(99.0)
        context = LoopContext(
            deck=_deck_context(deck, scored=True),
            tools=SlideFixTools(rewriter=_Rewriter([_answer()]), scorer=scorer),
            settings=SlideFixSettings(attempts=2),
        )
        result = await fix_slide(target, context)
        assert not result.fixed
        assert scorer.texts == []
        assert [a.outcome for a in result.attempts] == ["still_failing"] * 2
        assert result.issues[-1].code == "voice_score_low"
        assert current_text(result) == pt(deck, 4)["body"]

    async def test_unscored_deck_is_not_rescored(self) -> None:
        deck = prod_deck()
        target = SlideTarget(
            slide_index=4,
            record=deck[3],
            issues=(SlideIssue(code="x", message="y", locale="en", field="body"),),
        )
        scorer = _Scorer(10.0)
        body = "When I do not say where to stop, the agent rewrites whole modules."
        answer = json.dumps({"en": {"body": body}})
        context = LoopContext(
            deck=_deck_context(deck, scored=False),
            tools=SlideFixTools(rewriter=_Rewriter([answer]), scorer=scorer),
            settings=SlideFixSettings(attempts=1),
        )
        result = await fix_slide(target, context)
        assert result.fixed
        assert scorer.texts == []
        assert en([result.record], 1)["body"] == body


@pytest.mark.unit
class TestTargetsAndPrompt:
    def test_targets_list_every_failing_slide(self) -> None:
        deck = prod_deck()
        pt(deck, 4)["body"] = "Escopo aberto custa caro."
        state: dict[str, object] = {
            "persona_scores": {"slide_6": {"overall": 60}, "slide_x": 1, "other": 2},
            "outline": [{"slide_index": 4, "role": "point"}, "bad", {"role": "twist"}],
        }
        selection = select_targets(
            TargetQuery(
                records=deck,
                state=state,
                policy_version=POV,
                phase=PHASE_CONTENT,
                voice_floor=70.0,
            )
        )
        assert [t.slide_index for t in selection.targets] == [4, 6]
        assert selection.targets[0].role == "point"
        assert selection.targets[1].issues[0].code == "voice_score_low"
        assert selection.targets[1].score == 60.0
        assert selection.unfixable_rules == ()

    def test_carousel_wide_rules_are_unfixable(self) -> None:
        deck = prod_deck()[:5]
        selection = select_targets(
            TargetQuery(
                records=deck,
                state={},
                policy_version=POV,
                phase=PHASE_CONTENT,
                voice_floor=70.0,
            )
        )
        assert "slide_count_invalid" in selection.unfixable_rules

    @pytest.mark.parametrize(
        ("value", "expected"),
        [({"overall": 72}, 72.0), (55, 55.0), ({"overall": True}, None), ("x", None)],
    )
    def test_overall_score(self, value: object, expected: float | None) -> None:
        # AE-0407: an unreadable overall is unscored (None), not 0.
        assert overall_score(value) == expected

    def test_slide_scores_ignores_bad_shapes(self) -> None:
        assert slide_scores({"persona_scores": "bad"}) == {}
        assert slide_scores({"persona_scores": {"slide_2": 71}}) == {2: 71.0}

    def test_hook_prompt_asks_for_a_distinct_subline(self) -> None:
        deck = prod_deck()
        target = SlideTarget(
            slide_index=1,
            record=deck[0],
            issues=(SlideIssue(code="heading_repeated_in_body", message="m"),),
            role="hook",
        )
        policy = load_presentation_policy(POV)
        prompt = render_slide_fix_prompt(target, target.issues, (policy, "", 70.0))
        assert "DISTINCT" in prompt
        assert "role: hook" in prompt
        assert "at most 60 characters" in prompt
        point = render_slide_fix_prompt(
            SlideTarget(slide_index=8, record=deck[7], issues=()), (), (policy, "", 70)
        )
        assert "DISTINCT" not in point
        assert '"summary_points"' in point

    def test_issue_lines_name_locale_and_field(self) -> None:
        lines = issue_lines((
            SlideIssue(code="a", message="m", locale="pt", field="body"),
            SlideIssue(code="b", message="n"),
        ))
        assert lines == ["- a (pt body): m", "- b (slide copy): n"]

    def test_apply_answer_merges_items_by_position(self) -> None:
        record = prod_deck()[7]
        answer = json.dumps({
            "pt": {
                "heading": "Checklist para salvar",
                "summary_points": [
                    {"title": "Arquivos certos", "body": "Diga onde mexer."},
                    {"title": "", "body": "Liste o proibido."},
                    {"title": "Teste antes", "body": 3},
                ],
            },
            "en": {"features": [{"title": "x"}]},
        })
        updated = apply_answer(record, answer)
        assert updated is not None
        points = cast(list[dict[str, object]], pt([updated], 1)["summary_points"])
        assert [p["title"] for p in points] == [
            "Arquivos certos",
            "Fora do escopo",
            "Teste antes",
        ]
        assert points[0]["icon_name"] == "target"
        assert points[2]["body"] == "Peça o teste antes do código."

    @pytest.mark.parametrize(
        "answer",
        [
            "not json",
            json.dumps({"de": {"body": "x"}}),
            json.dumps({"pt": "x"}),
            json.dumps({"pt": {"summary_points": [{"title": "a"}]}}),
        ],
    )
    def test_unusable_answers(self, answer: str) -> None:
        record = prod_deck()[7]
        updated = apply_answer(record, answer)
        assert updated is None or updated == record

    def test_item_lists_of_another_size_are_ignored(self) -> None:
        record = prod_deck()[7]
        answer = json.dumps({"pt": {"summary_points": [{"title": "a", "body": "b"}]}})
        assert apply_answer(record, answer) == record
        bad = json.dumps({"pt": {"summary_points": ["a", "b", "c"]}})
        assert apply_answer(record, bad) == record

    def test_fix_patch_without_scores(self) -> None:
        deck = prod_deck()
        state: dict[str, object] = {
            "localized_slides": deck,
            "presentation_policy_version": POV,
        }
        result = SlideFixResult(
            slide_index=2, fixed=True, record=deck[1], issues=(), attempts=(), score=90
        )
        updates = fix_patch(state, [result])
        assert "persona_scores" not in updates
        scored = fix_patch(
            {**state, "persona_scores": {"slide_2": 50, "slide_3": 80}},
            [
                result,
                SlideFixResult(
                    slide_index=3, fixed=True, record=deck[2], issues=(), attempts=()
                ),
            ],
        )
        assert scored["persona_scores"] == {"slide_2": {"overall": 90}, "slide_3": 80}
