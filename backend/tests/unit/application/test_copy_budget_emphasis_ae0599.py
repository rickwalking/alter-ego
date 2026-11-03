"""Emphasis conversion, inline POV limits and the step's diagnostics.

Gherkin: tests/features/content_gate_after_copy_budget_ae0599.feature (A, C, D).
Every limit asserted here is read from the loaded contract, never retyped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from structlog.testing import capture_logs

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.application.services.carousel.content_budget_step import (
    BudgetStepInput,
    run_budget_step,
)
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    target_id,
)
from rag_backend.application.services.carousel.copy_budget_fit import (
    BudgetFitCommand,
    fit_slides_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_limits import (
    LimitScope,
    limits_payload,
)
from rag_backend.application.services.carousel.instruction_context_loader import (
    _limits_block,
    _sized_policy,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.domain.constants.copy_budget_fit import (
    COPY_BUDGET_LIMITS_PROMPT_VERSION,
    COPY_BUDGET_PROMPT_DOMAIN,
    COPY_BUDGET_PROMPT_LIMITS,
    LOG_COPY_BUDGET_FIT_DONE,
    LOG_COPY_BUDGET_FIT_VOICE_REVERTED,
    REJECT_NEW_VIOLATION,
    REJECT_NOT_SHORTER,
)
from rag_backend.domain.constants.pov_prompts import (
    POV_NEWS_PROMPT_DOMAIN,
    POV_PROMPT_CONTENT,
    POV_PROMPT_CONTENT_VERSION,
    POV_PROMPT_DOMAIN,
)
from rag_backend.domain.models.pov_prompts import (
    PovSlideContext,
    PovThesis,
    SlidePolicyContext,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from tests.unit.application.copy_budget_fit_fixtures_ae0588 import (
    EN_ANSWERS,
    EN_SENTENCES,
    PT_SENTENCES,
    FakeFitter,
    content_slide,
    locale_payload,
    localized_slide,
    prose,
)

POLICY = "pov_hook_v1"
PROMPTS = Path(__file__).parents[3] / "src/rag_backend/agents/prompts"
_DRAFT = json.dumps({"draft_text": "Copy", "confidence_score": 0.9})


def _over_budget_en(index: int = 3) -> dict[str, object]:
    long_en = "I see <strong>the team</strong> lose hours. " + prose(EN_SENTENCES, 240)
    return content_slide(index, pt_body=PT_SENTENCES[0], en_body=long_en)


def _id(index: int) -> str:
    return target_id(index, "en", "body")


def _command(
    slides: list[dict[str, object]],
    fitter: FakeFitter,
    excluded: frozenset[tuple[int, str, str]] = frozenset(),
) -> BudgetFitCommand:
    return BudgetFitCommand(
        slides=slides, fitter=fitter, policy_version=POLICY, excluded_fields=excluded
    )


def _en(slide: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], slide["presentation_en"])


@pytest.mark.unit
class TestAnswersInLocaleEmphasis:
    async def test_answer_with_pt_markers_is_converted(self) -> None:
        """Scenario: A fit answer in the other locale's markers is converted before it is checked."""
        answer = EN_ANSWERS[0].replace("I give", "I **give**")
        fitter = FakeFitter(answers={_id(3): answer})

        outcome = await fit_slides_to_budgets(_command([_over_budget_en()], fitter))

        body = str(_en(outcome.slides[0])["body"])
        assert "<strong>give</strong>" in body
        assert "**" not in body

    async def test_owner_hook_heading_keeps_its_markers(self) -> None:
        """Scenario: The owner's hook heading keeps its markers."""
        heading = "Revisão <strong>sem dono</strong> vira opinião"
        slide = localized_slide(
            1,
            locale_payload("intro", heading, "Eu explico."),
            locale_payload("intro", "Reviews **without owners** stall", "I explain."),
        )
        excluded = frozenset({(1, "pt", "heading")})

        outcome = await fit_slides_to_budgets(
            _command([slide], FakeFitter(), excluded=excluded)
        )

        fitted = outcome.slides[0]
        assert cast(dict[str, object], fitted["presentation_pt"])["heading"] == heading
        assert _en(fitted)["heading"] == "Reviews <strong>without owners</strong> stall"


@pytest.mark.unit
class TestDiagnostics:
    async def test_done_log_counts_dropped_rewrites_by_reason(self) -> None:
        """Scenario: The done log counts the dropped rewrites by reason."""
        slides = [_over_budget_en(3), _over_budget_en(4)]
        too_long = str(_en(slides[0])["body"]) + " Still more."
        lone_marker = "I give every request **an owner before it starts."
        fitter = FakeFitter(answers={_id(3): too_long, _id(4): lone_marker})

        with capture_logs() as logs:
            await fit_slides_to_budgets(
                BudgetFitCommand(
                    slides=slides, fitter=fitter, policy_version=POLICY, max_attempts=1
                )
            )

        done = next(log for log in logs if log["event"] == LOG_COPY_BUDGET_FIT_DONE)
        assert done["rejected_reasons"] == {
            REJECT_NOT_SHORTER: 1,
            REJECT_NEW_VIOLATION: 1,
        }

    async def test_voice_revert_is_logged_with_its_slides(self) -> None:
        """Scenario: A voice revert is logged with its slides."""
        slide = _over_budget_en(3)
        draft: dict[str, object] = {
            "slide_index": 3,
            "slide_type": "content",
            "policy_version": POLICY,
            "title": "Revisões precisam de um dono",
            "draft_text": PT_SENTENCES[0],
            "presentation_pt": slide["presentation_pt"],
            "presentation_en": slide["presentation_en"],
        }
        scorer = AsyncMock(
            return_value={"persona_scores": {"slide_1": {"overall": 60.0}}}
        )
        step = BudgetStepInput(
            project_id="p",
            slide_drafts=[draft],
            translations_en=None,
            scorer=scorer,
            previous_scores={"slide_1": {"overall": 80.0, "text_sha256": "old"}},
        )

        with capture_logs() as logs:
            fit = await run_budget_step(FakeFitter(), step, {})

        assert fit.slide_drafts[0] == draft
        reverted = [
            log for log in logs if log["event"] == LOG_COPY_BUDGET_FIT_VOICE_REVERTED
        ]
        assert [log["reverted_slides"] for log in reverted] == [[3]]


def _llm() -> AsyncMock:
    llm = AsyncMock()
    llm.bind = MagicMock(return_value=llm)
    llm.ainvoke.return_value = MagicMock(content=_DRAFT)
    return llm


def _sent(llm: AsyncMock) -> str:
    sent = llm.ainvoke.call_args.args[0]
    return "".join(str(message.content) for message in sent)


@pytest.mark.unit
class TestInlinePovLimits:
    @pytest.mark.parametrize(
        ("domain", "opening"),
        [
            (POV_PROMPT_DOMAIN, 'carrossel\n"Ponto de Vista", seguindo'),
            (POV_NEWS_PROMPT_DOMAIN, '"Ponto de Vista: Notícia"'),
        ],
    )
    async def test_content_prompt_carries_this_slides_limits(
        self, domain: str, opening: str
    ) -> None:
        """Scenario: The POV content prompt carries this slide's contract limits inline."""
        get_ai_response_cache().clear()
        llm = _llm()
        policy = SlidePolicyContext(
            policy_version=POLICY,
            slide_count=9,
            pov=PovSlideContext(
                pov=PovThesis(thesis="Revisão precisa de dono.", prompt_domain=domain),
                role="twist",
                slide_count=9,
            ),
        )

        await ContentDraftAgent(llm=llm).draft_slide(
            7, "Virada", ["dono"], policy=policy
        )

        content = _sent(llm).split(opening, 1)[1]
        sized = _sized_policy(load_presentation_policy(POLICY), 9)
        body = next(
            limit
            for limit in limits_payload(LimitScope("content", "twist"), sized)
            if limit["field"] == "body"
        )
        line = f"- body: at most {body['max_characters']} characters"
        assert line in content
        assert content.index(line) < content.index("Responda SOMENTE")


@pytest.mark.unit
class TestPromptVersions:
    def test_limits_block_states_items_and_emphasis_cost(self) -> None:
        """Scenario: The slide limits block no longer asks for English copy."""
        policy = load_presentation_policy(POLICY)

        block = _limits_block(LimitScope("content", "point"), policy)

        assert "apply to the Portuguese and to the English copy" not in block
        assert "a listed item limit is not a request to add items" in block
        assert "<strong>...</strong> (17 characters of markup)" in block

    def test_new_versions_are_the_defaults_and_old_ones_stay(self) -> None:
        """Scenario: The default prompt versions are the new ones."""
        assert POV_PROMPT_CONTENT_VERSION == "v4"
        assert COPY_BUDGET_LIMITS_PROMPT_VERSION == "v2"
        for domain in (POV_PROMPT_DOMAIN, POV_NEWS_PROMPT_DOMAIN):
            for version in ("v1", "v3", "v4"):
                assert (
                    PROMPTS / domain / version / f"{POV_PROMPT_CONTENT}.yaml"
                ).is_file()
        for version in ("v1", "v2"):
            limits = PROMPTS / COPY_BUDGET_PROMPT_DOMAIN / version
            assert (limits / f"{COPY_BUDGET_PROMPT_LIMITS}.yaml").is_file()
