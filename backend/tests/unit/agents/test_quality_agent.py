"""Unit tests for QualityAgent.

Feature: Quality rubric evaluation and scoring
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

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
    def mock_embeddings(self) -> AsyncMock:
        """Create a mock embedding service."""
        service = AsyncMock()
        service.embed_dense = AsyncMock(return_value=[[1.0, 0.0], [0.0, 1.0]])
        return service

    @pytest.fixture
    def agent(self, rubric: QualityRubric, mock_llm: AsyncMock) -> QualityAgent:
        """Create a QualityAgent instance."""
        return QualityAgent(rubric=rubric, llm=mock_llm)

    # Scenario: Evaluate content against rubric
    async def test_evaluate_returns_scores(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate is called, then scores are returned."""
        response_data = {
            "overall_score": 85.0,
            "criterion_scores": {
                "tone": {
                    "score": 85.0,
                    "weight": 0.5,
                    "passed": True,
                    "feedback": "Good",
                }
            },
            "feedback": ["Good job"],
            "passed": True,
        }
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(response_data))

        result = await agent.evaluate("test content")

        assert result["overall_score"] == 85.0
        assert result["passed"] is True
        assert "tone" in result["criteria_scores"]

    async def test_evaluate_prompt_includes_content_and_rubric(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate is called, then prompt includes rubric and content."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "feedback": [],
                "passed": True,
            })
        )

        await agent.evaluate("unique quality content abc")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "unique quality content abc" in prompt
        assert "Test Rubric" in prompt
        assert "Tone" in prompt
        assert "No sources provided" in prompt

    async def test_evaluate_without_sources_uses_default_label(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given no sources, when evaluating, then default sources label is used."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "feedback": [],
                "passed": True,
            })
        )

        await agent.evaluate("content")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "SOURCES USED:\nNo sources provided" in prompt

    async def test_evaluate_joins_multiple_sources_with_newlines(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given multiple sources, when evaluating, then sources are newline-joined."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "feedback": [],
                "passed": True,
            })
        )

        await agent.evaluate(
            "content", sources=["https://a.example", "https://b.example"]
        )

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "https://a.example\nhttps://b.example" in prompt

    async def test_evaluate_passes_langfuse_callbacks(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given evaluate call, when invoking LLM, then Langfuse callbacks are attached."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "feedback": [],
                "passed": True,
            })
        )
        handler = MagicMock()

        with patch(
            "rag_backend.agents.quality_agent.get_langfuse_handler",
            return_value=[handler],
        ) as mock_handler:
            await agent.evaluate("content")

        mock_handler.assert_called_once()
        assert mock_llm.ainvoke.call_args.kwargs["callbacks"] == [handler]

    async def test_evaluate_with_sources(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content and sources, when evaluate is called, then sources included in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criteria_scores": {},
                "feedback": [],
                "passed": True,
            })
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

    def test_parse_evaluation_response_preserves_criterion_details(
        self, agent: QualityAgent
    ) -> None:
        """Given criterion scores JSON, when parsing, then nested fields are preserved."""
        response = json.dumps({
            "overall_score": 82.0,
            "criterion_scores": {
                "tone": {
                    "score": 82.0,
                    "weight": 0.5,
                    "passed": True,
                    "feedback": "Strong tone",
                }
            },
            "feedback": ["Nice work"],
            "passed": True,
        })

        result = agent._parse_evaluation_response(response)

        tone = result["criteria_scores"]["tone"]
        assert tone["score"] == 82.0
        assert tone["weight"] == 0.5
        assert tone["passed"] is True
        assert tone["feedback"] == "Strong tone"
        assert result["feedback"] == ["Nice work"]

    def test_build_evaluation_prompt_includes_all_sections(
        self, agent: QualityAgent
    ) -> None:
        """Given content and sources, when building prompt, then all sections are present."""
        prompt = agent._build_evaluation_prompt("my content", "source one")

        assert "Test Rubric" in prompt
        assert "my content" in prompt
        assert "source one" in prompt
        assert "carousel" in prompt
        assert "Tone" in prompt

    # Scenario: Evaluate single criterion
    async def test_evaluate_criterion_with_ai_auto(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given AI_AUTO criterion, when evaluate_criterion is called, then AI evaluation used."""
        mock_llm.ainvoke.return_value = MagicMock(content="85.0")

        criterion = agent.rubric.criteria[0]
        score = await agent.evaluate_criterion(criterion, "content")

        assert score == 85.0

    async def test_evaluate_criterion_prompt_includes_content(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluating criterion, then prompt includes it."""
        mock_llm.ainvoke.return_value = MagicMock(content="88.0")
        criterion = agent.rubric.criteria[0]

        await agent.evaluate_criterion(criterion, "slide copy text")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "slide copy text" in prompt
        assert "Evaluate tone:" in prompt

    async def test_evaluate_criterion_with_human_required(
        self, agent: QualityAgent
    ) -> None:
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

    def test_cosine_similarity_returns_zero_for_zero_vector(
        self, agent: QualityAgent
    ) -> None:
        """Given zero vector, when calculating similarity, then zero is returned."""
        assert agent._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    # Scenario: Generate improvement suggestions
    async def test_generate_suggestions_below_threshold(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given score below threshold, when generating suggestions, then suggestions returned."""
        mock_llm.ainvoke.return_value = MagicMock(
            content="- Improve tone\n- Add examples"
        )

        criterion = agent.rubric.criteria[0]
        suggestions = await agent.generate_improvement_suggestions(
            criterion, "content", 60.0
        )

        assert len(suggestions) > 0

    async def test_generate_suggestions_prompt_includes_content(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given failing score, when generating suggestions, then content is in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(content="- Improve tone")

        criterion = agent.rubric.criteria[0]
        await agent.generate_improvement_suggestions(
            criterion, "failing content xyz", 60.0
        )

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "failing content xyz" in prompt
        assert "Tone" in prompt
        assert "60.0/100" in prompt

    async def test_generate_suggestions_above_threshold(
        self, agent: QualityAgent
    ) -> None:
        """Given score above threshold, when generating suggestions, then empty list returned."""
        criterion = agent.rubric.criteria[0]
        suggestions = await agent.generate_improvement_suggestions(
            criterion, "content", 80.0
        )

        assert suggestions == []

    # Scenario: Calculate originality
    async def test_calculate_originality_with_sources(
        self, agent: QualityAgent
    ) -> None:
        """Given content and sources, when calculating originality, then score is calculated."""
        score = await agent.calculate_originality("content", ["source1", "source2"])

        assert score > 50.0
        assert score <= 100.0

    async def test_calculate_originality_without_sources(
        self, agent: QualityAgent
    ) -> None:
        """Given content without sources, when calculating originality, then base score returned."""
        score = await agent.calculate_originality("content", [])

        assert pytest.approx(score, abs=0.01) == 50.0

    async def test_calculate_originality_with_embedding_service(
        self,
        rubric: QualityRubric,
        mock_llm: AsyncMock,
        mock_embeddings: AsyncMock,
    ) -> None:
        """Given embeddings, when calculating originality, then similarity drives score."""
        agent = QualityAgent(
            rubric=rubric, llm=mock_llm, embedding_service=mock_embeddings
        )

        score = await agent.calculate_originality("unique content", ["source text"])

        assert score == 100.0
        mock_embeddings.embed_dense.assert_awaited_once()

    async def test_calculate_originality_with_identical_embeddings(
        self, rubric: QualityRubric, mock_llm: AsyncMock
    ) -> None:
        """Given identical embeddings, when calculating originality, then score is zero."""
        embeddings = AsyncMock()
        embeddings.embed_dense = AsyncMock(return_value=[[1.0, 0.0], [1.0, 0.0]])
        agent = QualityAgent(rubric=rubric, llm=mock_llm, embedding_service=embeddings)

        score = await agent.calculate_originality("same text", ["same text"])

        assert score == 0.0

    async def test_calculate_originality_bonus_without_embedding_service(
        self, agent: QualityAgent
    ) -> None:
        """Given multiple sources without embeddings, when calculating, then bonus applies."""
        score = await agent.calculate_originality("content", ["s1", "s2", "s3"])

        assert score > 50.0

    # Scenario: Evaluate E-E-A-T
    async def test_evaluate_eeat(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
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

    async def test_evaluate_eeat_prompt_includes_content(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluating E-E-A-T, then prompt includes truncated content."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"overall_eeat": 70.0})
        )

        await agent.evaluate_eeat("unique eeat content marker", ["source"])

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "unique eeat content marker" in prompt
        assert "source" in prompt

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
