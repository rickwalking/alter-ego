"""The carousel's quality rubric reaches every content prompt and the judge.

Feature: backend/tests/features/carousel_rubric_ae0504.feature
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.carousel_rubric_judge import (
    CarouselRubricJudge,
    parse_judge_answer,
    render_rubric_criteria,
)
from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
    PRESENTATION_POLICY_VERSION_POV_HOOK_V1,
)
from rag_backend.domain.models.carousel_rubric import (
    CarouselRubric,
    RubricJudgeRequest,
)
from rag_backend.domain.models.pov_prompts import (
    PovSlideContext,
    PovThesis,
    SlidePolicyContext,
)
from rag_backend.domain.models.rubric import (
    EvaluationMethod,
    RubricCriterion,
    ScoringScale,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache

RUBRIC = CarouselRubric(
    id="rubric-qa",
    name="Rubrica QA",
    criteria=(
        RubricCriterion(
            id="clarity",
            name="Clareza",
            description="Cada slide diz uma coisa só",
            weight=1.0,
            evaluation_method=EvaluationMethod.AI_AUTO,
            min_threshold=0.7,
            scoring_scale=ScoringScale.SCORE_0_100,
            prompt_template="Avalie a clareza de {content} usando {sources}",
        ),
        RubricCriterion(
            id="proof",
            name="Prova",
            description="Toda afirmação tem um exemplo",
            weight=1.0,
            evaluation_method=EvaluationMethod.AI_AUTO,
            min_threshold=7.0,
            scoring_scale=ScoringScale.SCORE_1_10,
            prompt_template="",
        ),
    ),
)
DRAFT = json.dumps({"draft_text": "Copy", "confidence_score": 0.9, "sources_used": []})
POV = PovThesis(thesis="IA não substitui revisão")
POLICIES: dict[str, SlidePolicyContext | None] = {
    "generic": None,
    "radar": SlidePolicyContext(
        policy_version=PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
        slide_count=7,
        role="hook",
        hook_text="Gancho",
    ),
    "pov": SlidePolicyContext(
        policy_version=PRESENTATION_POLICY_VERSION_POV_HOOK_V1,
        slide_count=7,
        pov=PovSlideContext(pov=POV, role="hook", slide_count=7),
    ),
    "pov_news": SlidePolicyContext(
        policy_version=PRESENTATION_POLICY_VERSION_POV_HOOK_V1,
        slide_count=7,
        pov=PovSlideContext(
            pov=PovThesis(thesis="x", prompt_domain="carousel_pov_news"),
            role="hook",
            slide_count=7,
        ),
    ),
}


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_ai_response_cache().clear()


def _llm() -> AsyncMock:
    llm = AsyncMock()
    llm.bind = MagicMock(return_value=llm)
    llm.ainvoke.return_value = MagicMock(content=DRAFT)
    return llm


def _sent_prompt(llm: AsyncMock) -> str:
    sent = llm.ainvoke.call_args.args[0]
    if isinstance(sent, list):
        return "".join(str(message.content) for message in sent)
    return str(sent)


def test_rubric_block_names_every_criterion_field() -> None:
    """Scenario: Every content prompt carries the rubric's criteria."""
    block = render_rubric_criteria(RUBRIC)

    assert "Rubrica QA" in block
    assert "Clareza" in block and "Cada slide diz uma coisa só" in block
    assert "Avalie a clareza de  usando" in block
    assert "{content}" not in block and "{sources}" not in block
    assert "scale 0-100; must reach 70/100" in block
    assert "Prova" in block and "scale 1-10; must reach 70/100" in block


@pytest.mark.parametrize("variant", sorted(POLICIES))
async def test_every_content_prompt_ends_with_the_rubric(variant: str) -> None:
    """Scenario: Every content prompt carries the rubric's criteria."""
    llm = _llm()
    agent = ContentDraftAgent(llm=llm).with_rubric(RUBRIC)

    await agent.draft_slide(1, "Título", ["Ponto"], policy=POLICIES[variant])

    prompt = _sent_prompt(llm)
    assert prompt.endswith(render_rubric_criteria(RUBRIC))


async def test_without_a_rubric_the_prompt_is_unchanged() -> None:
    """Scenario: Every content prompt carries the rubric's criteria."""
    plain_llm, rubric_llm = _llm(), _llm()
    plain = ContentDraftAgent(llm=plain_llm)

    assert plain.with_rubric(None) is plain
    assert plain.with_rubric(CarouselRubric(id="e", name="E", criteria=())) is plain
    await plain.draft_slide(1, "Título", ["Ponto"])
    get_ai_response_cache().clear()
    await (
        ContentDraftAgent(llm=rubric_llm)
        .with_rubric(RUBRIC)
        .draft_slide(1, "Título", ["Ponto"])
    )

    assert "Rubrica QA" not in _sent_prompt(plain_llm)
    assert _sent_prompt(rubric_llm).startswith(_sent_prompt(plain_llm))


async def test_judge_scores_on_the_hundred_scale() -> None:
    """Scenario: The drafted carousel is scored on 0-100 per criterion."""
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(
        content=json.dumps({
            "criteria": [
                {"id": "clarity", "score": 82, "feedback": "Claro"},
                {"id": "proof", "score": 55, "feedback": "Falta exemplo"},
            ],
            "feedback": "Bom",
        })
    )

    evaluation = await CarouselRubricJudge(llm).score(
        RubricJudgeRequest(rubric=RUBRIC, content="Slide 1: Copy", project_id="p1")
    )

    prompt = _sent_prompt(llm)
    assert "integer from 0 to 100" in prompt
    assert "id: clarity" in prompt and "Slide 1: Copy" in prompt
    assert [(c.score, c.passed) for c in evaluation.criteria] == [
        (82, True),
        (55, False),
    ]
    assert evaluation.overall_score == 68
    assert evaluation.feedback == "Bom"


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        json.dumps({"criteria": "none"}),
        json.dumps({"criteria": ["x"]}),
        json.dumps({"criteria": [{"id": "c", "score": "high"}]}),
        json.dumps({"criteria": [{"id": "c", "score": True}]}),
    ],
)
def test_malformed_judge_answers_are_rejected(raw: str) -> None:
    """Scenario: A judge failure leaves the run going without scores."""
    with pytest.raises((ValueError, TypeError)):
        parse_judge_answer(raw)


def test_fenced_judge_answer_parses() -> None:
    """Scenario: The drafted carousel is scored on 0-100 per criterion."""
    answers, feedback = parse_judge_answer(
        '```json\n{"criteria": [{"id": "clarity", "score": 70.5}]}\n```'
    )
    assert [(a.criterion_id, a.score, a.feedback) for a in answers] == [
        ("clarity", 70.5, "")
    ]
    assert feedback == ""
