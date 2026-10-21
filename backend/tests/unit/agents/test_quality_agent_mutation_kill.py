"""Assertion-bearing tests that pin exact QualityAgent behaviour.

Feature: Quality rubric evaluation and scoring
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.agents import quality_agent as quality_module
from rag_backend.agents.quality_agent import QualityAgent
from rag_backend.domain.models.rubric import (
    EvaluationMethod,
    QualityRubric,
    RubricCriterion,
    ScoringScale,
)

RUBRIC_DESCRIPTION = "Rubric description marker"
CRITERION_DESCRIPTION = "Criterion description marker"
CRITERION_THRESHOLD = 73.0
RUNNABLE_CONFIG = {"callbacks": ["langfuse-marker"]}
CONFIG_PATH = "rag_backend.agents.quality_agent.get_langfuse_runnable_config"
RENDER_PATH = "rag_backend.agents.quality_agent.render_prompt"


def _criterion(template: str = "Score: {content} | {sources}") -> RubricCriterion:
    """Build an AI-auto criterion with distinctive fields."""
    return {
        "id": "clarity",
        "name": "Clarity",
        "description": CRITERION_DESCRIPTION,
        "weight": 1.0,
        "evaluation_method": EvaluationMethod.AI_AUTO,
        "min_threshold": CRITERION_THRESHOLD,
        "scoring_scale": ScoringScale.SCORE_0_100,
        "prompt_template": template,
    }


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Create a mock LLM returning an empty JSON object."""
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(content="{}")
    return llm


@pytest.fixture
def agent(mock_llm: AsyncMock) -> QualityAgent:
    """Create a QualityAgent with a distinctive rubric."""
    rubric = QualityRubric(
        name="Rubric",
        description=RUBRIC_DESCRIPTION,
        applicable_content_types=["carousel"],
        criteria=[_criterion()],
    )
    return QualityAgent(rubric=rubric, llm=mock_llm)


def _sent_prompt(mock_llm: AsyncMock) -> str:
    """Return the prompt text sent to the LLM on the last call."""
    return str(mock_llm.ainvoke.call_args[0][0][0].content)


def _sent_config(mock_llm: AsyncMock) -> object:
    """Return the runnable config positional argument of the last LLM call."""
    return mock_llm.ainvoke.call_args[0][1]


# Scenario: Evaluation prompt carries the rubric description
def test_build_prompt_renders_rubric_description(agent: QualityAgent) -> None:
    """The rubric description reaches the rendered evaluation prompt."""
    prompt = agent._build_evaluation_prompt("content", "sources")

    assert f"DESCRIPTION: {RUBRIC_DESCRIPTION}" in prompt


# Scenario: Missing criterion scores keep the top-level fields
def test_parse_without_criterion_scores_keeps_overall_score(
    agent: QualityAgent,
) -> None:
    """A response without criterion_scores keeps the parsed top-level values."""
    payload = json.dumps({"overall_score": 81, "passed": True, "feedback": ["ok"]})

    result = agent._parse_evaluation_response(payload)

    assert result == {
        "overall_score": 81.0,
        "criteria_scores": {},
        "feedback": ["ok"],
        "passed": True,
    }


# Scenario: AI criterion evaluation forwards the given sources
async def test_evaluate_criterion_forwards_sources(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """Sources given to evaluate_criterion appear in the formatted prompt."""
    mock_llm.ainvoke.return_value = MagicMock(content="64")

    score = await agent.evaluate_criterion(_criterion(), "body", ["src-one"])

    assert score == 64.0
    assert _sent_prompt(mock_llm) == "Score: body | ['src-one']"


# Scenario: AI criterion evaluation without sources formats an empty list
async def test_evaluate_criterion_without_sources_formats_empty_list(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """No sources are formatted as an empty list, never as None."""
    await agent.evaluate_criterion(_criterion(), "body")

    assert _sent_prompt(mock_llm) == "Score: body | []"


# Scenario: Every LLM call is traced with the Langfuse runnable config
async def test_all_llm_calls_pass_langfuse_config(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """Criterion, suggestion and E-E-A-T calls pass the runnable config."""
    with patch(CONFIG_PATH, return_value=RUNNABLE_CONFIG):
        await agent.evaluate_criterion(_criterion(), "body")
        assert _sent_config(mock_llm) == RUNNABLE_CONFIG
        await agent.generate_improvement_suggestions(_criterion(), "body", 10.0)
        assert _sent_config(mock_llm) == RUNNABLE_CONFIG
        await agent.evaluate_eeat("body", [])
        assert _sent_config(mock_llm) == RUNNABLE_CONFIG


# Scenario: Improvement prompt carries the criterion description and threshold
async def test_suggestions_prompt_renders_description_and_threshold(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """The improvement prompt renders the description and the threshold."""
    mock_llm.ainvoke.return_value = MagicMock(content="- one")

    await agent.generate_improvement_suggestions(_criterion(), "body", 10.0)

    prompt = _sent_prompt(mock_llm)
    assert f"DESCRIPTION: {CRITERION_DESCRIPTION}" in prompt
    assert f"THRESHOLD: {CRITERION_THRESHOLD}/100" in prompt


# Scenario: Improvement prompt falls back when the registry fails
async def test_suggestions_use_fallback_prompt_on_registry_error(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """A registry failure sends the improvement fallback prompt."""
    mock_llm.ainvoke.return_value = MagicMock(content="- one")

    with patch(RENDER_PATH, side_effect=RuntimeError("down")):
        await agent.generate_improvement_suggestions(_criterion(), "body", 10.0)

    assert _sent_prompt(mock_llm) == quality_module._IMPROVE_PROMPT_FALLBACK


# Scenario: E-E-A-T prompt falls back when the registry fails
async def test_eeat_uses_fallback_prompt_on_registry_error(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """A registry failure sends the E-E-A-T fallback prompt."""
    with patch(RENDER_PATH, side_effect=RuntimeError("down")):
        await agent.evaluate_eeat("body", [])

    assert _sent_prompt(mock_llm) == quality_module._EEAT_PROMPT_FALLBACK


# Scenario: E-E-A-T preview is capped at 500 characters
async def test_eeat_content_preview_is_first_500_chars(agent: QualityAgent) -> None:
    """The E-E-A-T content preview holds exactly the first 500 characters."""
    content = "a" * 500 + "b" * 100

    with patch(RENDER_PATH, return_value=("prompt", {})) as render:
        await agent.evaluate_eeat(content, ["s"])

    variables = render.call_args[0][2]
    assert variables["content_preview"] == "a" * 500
    assert variables["sources"] == ["s"]


# Scenario: E-E-A-T keeps each provided dimension and defaults the rest to 50
async def test_eeat_reads_each_dimension_and_defaults_missing(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """Each provided dimension is read by its exact key; missing ones are 50."""
    payload = {"expertise": 81, "authoritativeness": 82, "trustworthiness": 83}
    mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))

    result = await agent.evaluate_eeat("body", [])

    assert result == {
        "experience": 50.0,
        "expertise": 81.0,
        "authoritativeness": 82.0,
        "trustworthiness": 83.0,
        "overall_eeat": 50.0,
    }


# Scenario: E-E-A-T defaults experience and overall when only one is given
async def test_eeat_defaults_overall_when_only_experience_given(
    agent: QualityAgent, mock_llm: AsyncMock
) -> None:
    """A provided experience is kept while overall_eeat defaults to 50."""
    mock_llm.ainvoke.return_value = MagicMock(content=json.dumps({"experience": 90}))

    result = await agent.evaluate_eeat("body", [])

    assert result["experience"] == 90.0
    assert result["overall_eeat"] == 50.0
    assert result["expertise"] == 50.0


# Scenario: Originality heuristic adds ten points per source
async def test_originality_heuristic_single_source_bonus(agent: QualityAgent) -> None:
    """One source without an embedding service adds exactly ten points."""
    score = await agent.calculate_originality("", ["only"])

    assert score == 60.0


# Scenario: Originality embeds the content followed by the sources
async def test_originality_embeds_content_then_sources(mock_llm: AsyncMock) -> None:
    """Embeddings are requested for [content, *sources] in order."""
    service = AsyncMock()
    service.embed_dense = AsyncMock(return_value=[[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    rubric = QualityRubric(name="r", description="d", criteria=[_criterion()])
    agent = QualityAgent(rubric=rubric, llm=mock_llm, embedding_service=service)

    score = await agent.calculate_originality("body", ["s1", "s2"])

    service.embed_dense.assert_awaited_once_with(["body", "s1", "s2"])
    assert score == 29.29


# Scenario: Originality is rounded to two decimals
async def test_originality_rounds_to_two_decimals(mock_llm: AsyncMock) -> None:
    """A fractional originality keeps exactly two decimals."""
    service = AsyncMock()
    service.embed_dense = AsyncMock(return_value=[[1.0, 0.0], [0.4, 0.3]])
    rubric = QualityRubric(name="r", description="d", criteria=[_criterion()])
    agent = QualityAgent(rubric=rubric, llm=mock_llm, embedding_service=service)

    score = await agent.calculate_originality("body", ["s1"])

    assert score == 20.0
    service.embed_dense.return_value = [[1.0, 0.0], [0.6, 0.8]]
    assert await agent.calculate_originality("body", ["s1"]) == 40.0
    service.embed_dense.return_value = [[3.0, 1.0], [1.0, 1.0]]
    assert await agent.calculate_originality("body", ["s1"]) == 10.56


# Scenario: Cosine similarity uses both norms
def test_cosine_similarity_exact_value(agent: QualityAgent) -> None:
    """Cosine similarity divides by the product of both norms."""
    assert agent._cosine_similarity([1.0, 0.0], [2.0, 0.0]) == 1.0
    assert agent._cosine_similarity([3.0, 4.0], [3.0, 4.0]) == pytest.approx(1.0)


# Scenario: Cosine similarity rejects vectors of different length
def test_cosine_similarity_rejects_length_mismatch(agent: QualityAgent) -> None:
    """Vectors of different length raise instead of being truncated."""
    with pytest.raises(ValueError):
        agent._cosine_similarity([1.0, 0.0, 1.0], [1.0, 0.0])
