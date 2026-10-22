"""Rubric thresholds on one scale; safe prompt-template substitution.

Gherkin: tests/features/rubric_evaluation_ae0452.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from rag_backend.agents.quality_agent import QualityAgent
from rag_backend.api.schemas.persona_rubric import QualityRubricResponse
from rag_backend.api.schemas.persona_rubric import RubricCriterion as CriterionSchema
from rag_backend.application.services.phase5_migration_service import (
    _default_rubric_criteria,
)
from rag_backend.domain.models.rubric import (
    EvaluationMethod,
    QualityRubric,
    RubricCriterion,
    ScoringScale,
)


def _criterion(
    threshold: float,
    scale: ScoringScale = ScoringScale.SCORE_0_100,
    template: str = "Rate: {content}",
) -> RubricCriterion:
    return {
        "id": "clarity",
        "name": "Clarity",
        "description": "Clear",
        "weight": 1.0,
        "evaluation_method": EvaluationMethod.AI_AUTO,
        "min_threshold": threshold,
        "scoring_scale": scale,
        "prompt_template": template,
    }


@pytest.fixture
def llm() -> AsyncMock:
    model = AsyncMock()
    model.ainvoke.return_value = MagicMock(content="- tighten the intro")
    return model


@pytest.fixture
def agent(llm: AsyncMock) -> QualityAgent:
    return QualityAgent(rubric=QualityRubric(), llm=llm)


def _prompt(llm: AsyncMock) -> str:
    return str(llm.ainvoke.call_args[0][0][0].content)


# Scenario: A score below the threshold fails the criterion
async def test_score_below_fraction_threshold_gets_suggestions(
    agent: QualityAgent, llm: AsyncMock
) -> None:
    suggestions = await agent.generate_improvement_suggestions(
        _criterion(0.7), "body", 69.9
    )

    assert suggestions == ["tighten the intro"]
    assert "THRESHOLD: 70.0/100" in _prompt(llm)


# Scenario: A score at the threshold passes the criterion
async def test_score_at_fraction_threshold_passes(
    agent: QualityAgent, llm: AsyncMock
) -> None:
    suggestions = await agent.generate_improvement_suggestions(
        _criterion(0.7), "body", 70.0
    )

    assert suggestions == []
    llm.ainvoke.assert_not_called()


# Scenario: A 1-10 criterion compares on its own scale
async def test_one_to_ten_scale_compares_on_its_scale(agent: QualityAgent) -> None:
    failing = await agent.generate_improvement_suggestions(
        _criterion(0.8, ScoringScale.SCORE_1_10), "body", 7.0
    )
    passing = await agent.generate_improvement_suggestions(
        _criterion(0.8, ScoringScale.SCORE_1_10), "body", 8.0
    )

    assert failing == ["tighten the intro"]
    assert passing == []


# Scenario: A legacy percentage threshold is read as a fraction
async def test_legacy_percentage_threshold_still_compares(
    agent: QualityAgent,
) -> None:
    assert await agent.generate_improvement_suggestions(
        _criterion(70.0), "body", 69.0
    ) == ["tighten the intro"]
    assert (
        await agent.generate_improvement_suggestions(_criterion(70.0), "body", 70.0)
        == []
    )


# Scenario: A legacy percentage threshold is read as a fraction
def test_response_reads_legacy_percentage_as_fraction() -> None:
    response = QualityRubricResponse.model_validate({
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Seeded",
        "criteria": [{**_criterion(70.0)}],
        "applicable_content_types": ["carousel"],
        "is_default": True,
        "created_at": "2026-10-22T00:00:00Z",
        "updated_at": "2026-10-22T00:00:00Z",
        "version": 1,
    })

    assert response.criteria[0].min_threshold == pytest.approx(0.7)


# Scenario: Creating or updating a rubric with a threshold above 1.0 is rejected
@pytest.mark.parametrize("threshold", [1.5, 7.0, 70.0])
def test_input_schema_rejects_a_threshold_above_one(threshold: float) -> None:
    with pytest.raises(ValidationError):
        CriterionSchema.model_validate({**_criterion(threshold)})


# Scenario: The default editorial rubric uses fraction thresholds
def test_default_rubric_thresholds_are_fractions() -> None:
    criteria = _default_rubric_criteria()

    assert criteria
    for criterion in criteria:
        threshold = criterion["min_threshold"]
        assert isinstance(threshold, float)
        assert 0.0 < threshold <= 1.0
        CriterionSchema.model_validate(criterion)


# Scenario: A prompt template with other braces does not crash the evaluation
async def test_template_with_literal_braces_is_rendered(
    agent: QualityAgent, llm: AsyncMock
) -> None:
    llm.ainvoke.return_value = MagicMock(content="82")
    template = 'Rate {content} and answer as {"score": <0-100>} using {sources}'

    score = await agent.evaluate_criterion(
        _criterion(0.7, template=template), "the post", ["a.com"]
    )

    assert score == 82.0
    assert _prompt(llm) == (
        "Rate the post and answer as {\"score\": <0-100>} using ['a.com']"
    )


# Scenario: Content that contains a placeholder is not substituted again
async def test_placeholder_inside_content_is_not_substituted(
    agent: QualityAgent, llm: AsyncMock
) -> None:
    llm.ainvoke.return_value = MagicMock(content="50")

    await agent.evaluate_criterion(
        _criterion(0.7, template="{content} / {sources}"), "use {sources}", ["s"]
    )

    assert _prompt(llm) == "use {sources} / ['s']"
