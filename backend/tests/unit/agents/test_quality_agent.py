"""Unit tests for QualityAgent.

Feature: Quality rubric evaluation and scoring
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.quality_agent import QualityAgent
from rag_backend.domain.models.rubric import EvaluationMethod, QualityRubric


class TestQualityAgent:
    """Tests for QualityAgent."""

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        """Create a mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def rubric(self) -> QualityRubric:
        """Create a test rubric."""
        return QualityRubric(
            name="Test Rubric",
            description="Test rubric for unit tests",
            applicable_content_types=["carousel"],
            criteria=[
                {
                    "id": "tone",
                    "name": "Tone",
                    "description": "Check tone",
                    "weight": 0.5,
                    "evaluation_method": EvaluationMethod.AI_AUTO,
                    "min_threshold": 70.0,
                    "scoring_scale": "0-100",
                    "prompt_template": "Evaluate tone: {content}",
                }
            ],
        )

    @pytest.fixture
    def agent(self, rubric: QualityRubric, mock_llm: AsyncMock) -> QualityAgent:
        """Create a QualityAgent instance."""
        return QualityAgent(rubric=rubric, llm=mock_llm)

    # Scenario: Evaluate content against rubric
    async def test_evaluate_returns_scores(self, agent: QualityAgent, mock_llm: AsyncMock) -> None:
        """Given content, when evaluate is called, then scores are returned."""
        response_data = {
            "overall_score": 85.0,
            "criterion_scores": {
                "tone": {"score": 85.0, "weight": 0.5, "passed": True, "feedback": "Good"}
            },
            "feedback": ["Good job"],
            "passed": True,
        }
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(response_data))

        result = await agent.evaluate("test content")

        assert result["overall_score"] == 85.0
        assert result["passed"] is True
        assert "tone" in result["criteria_scores"]

    async def test_evaluate_with_sources(self, agent: QualityAgent, mock_llm: AsyncMock) -> None:
        """Given content and sources, when evaluate is called, then sources included in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "overall_score": 80.0,
                    "criteria_scores": {},
                    "feedback": [],
                    "passed": True,
                }
            )
        )

        await agent.evaluate("content", sources=["http://example.com"])

        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "http://example.com" in call_args[0].content

    async def test_evaluate_handles_invalid_json(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given invalid JSON response, when evaluate is called, then defaults returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="not json")

        result = await agent.evaluate("content")

        assert result["overall_score"] == 0.0
        assert result["passed"] is False

    # Scenario: Evaluate single criterion
    async def test_evaluate_criterion_with_ai_auto(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given AI_AUTO criterion, when evaluate_criterion is called, then AI evaluation used."""
        mock_llm.ainvoke.return_value = MagicMock(content="85.0")

        criterion = agent.rubric.criteria[0]
        score = await agent.evaluate_criterion(criterion, "content")

        assert score == 85.0

    async def test_evaluate_criterion_with_human_required(self, agent: QualityAgent) -> None:
        """Given HUMAN_REQUIRED criterion, when evaluate_criterion called, then default returned."""
        criterion = {
            "id": "human",
            "name": "Human Check",
            "description": "Needs human",
            "weight": 0.5,
            "evaluation_method": EvaluationMethod.HUMAN_REQUIRED,
            "min_threshold": 70.0,
            "scoring_scale": "0-100",
            "prompt_template": "Human check: {content}",
        }

        score = await agent.evaluate_criterion(criterion, "content")

        assert score == 75.0

    # Scenario: Extract score from LLM response
    def test_extract_score_with_number(self, agent: QualityAgent) -> None:
        """Given response with number, when extracting score, then number is parsed."""
        score = agent._extract_score("The score is 85.5")

        assert score == 85.5

    def test_extract_score_with_no_number(self, agent: QualityAgent) -> None:
        """Given response without number, when extracting score, then default is returned."""
        score = agent._extract_score("No score here")

        assert score == 50.0

    # Scenario: Generate improvement suggestions
    async def test_generate_suggestions_below_threshold(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given score below threshold, when generating suggestions, then suggestions returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="- Improve tone\n- Add examples")

        criterion = agent.rubric.criteria[0]
        suggestions = await agent.generate_improvement_suggestions(criterion, "content", 60.0)

        assert len(suggestions) > 0

    async def test_generate_suggestions_above_threshold(self, agent: QualityAgent) -> None:
        """Given score above threshold, when generating suggestions, then empty list returned."""
        criterion = agent.rubric.criteria[0]
        suggestions = await agent.generate_improvement_suggestions(criterion, "content", 80.0)

        assert suggestions == []

    # Scenario: Calculate originality
    async def test_calculate_originality_with_sources(self, agent: QualityAgent) -> None:
        """Given content and sources, when calculating originality, then score is calculated."""
        score = await agent.calculate_originality("content", ["source1", "source2"])

        assert score > 50.0
        assert score <= 100.0

    async def test_calculate_originality_without_sources(self, agent: QualityAgent) -> None:
        """Given content without sources, when calculating originality, then base score returned."""
        score = await agent.calculate_originality("content", [])

        assert pytest.approx(score, abs=0.01) == 50.0

    # Scenario: Evaluate E-E-A-T
    async def test_evaluate_eeat(self, agent: QualityAgent, mock_llm: AsyncMock) -> None:
        """Given content and sources, when evaluating E-E-A-T, then dimensions are scored."""
        response_data = {
            "experience": 80.0,
            "expertise": 85.0,
            "authoritativeness": 90.0,
            "trustworthiness": 95.0,
            "overall_eeat": 87.5,
        }
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(response_data))

        result = await agent.evaluate_eeat("content", ["source"])

        assert result["experience"] == 80.0
        assert result["overall_eeat"] == 87.5

    async def test_evaluate_eeat_invalid_json(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given invalid JSON, when evaluating E-E-A-T, then defaults returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="not json")

        result = await agent.evaluate_eeat("content", ["source"])

        assert result["experience"] == 50.0
        assert result["overall_eeat"] == 50.0

    # Scenario: Handle LLM errors
    async def test_evaluate_propagates_llm_errors(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given LLM raises error, when evaluate is called, then error is propagated."""
        mock_llm.ainvoke.side_effect = Exception("LLM error")

        with pytest.raises(Exception, match="LLM error"):
            await agent.evaluate("content")
