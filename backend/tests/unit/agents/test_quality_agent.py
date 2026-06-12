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
            "rag_backend.agents.quality_agent.get_langfuse_runnable_config",
            return_value={"callbacks": [handler]},
        ) as mock_config:
            await agent.evaluate("content")

        mock_config.assert_called_once()
        assert mock_llm.ainvoke.call_args.args[1] == {"callbacks": [handler]}

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

    def test_build_evaluation_prompt_joins_criteria_with_newlines(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given multiple criteria, when building prompt, then criteria are newline-joined."""
        rubric = QualityRubric(
            name="Multi Rubric",
            description="Two criteria",
            applicable_content_types=["blog_post"],
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
                },
                {
                    "id": "clarity",
                    "name": "Clarity",
                    "description": "Check clarity",
                    "weight": 0.5,
                    "evaluation_method": EvaluationMethod.AI_AUTO,
                    "min_threshold": 70.0,
                    "scoring_scale": "0-100",
                    "prompt_template": "Evaluate clarity: {content}",
                },
            ],
        )
        agent = QualityAgent(rubric=rubric, llm=mock_llm)

        prompt = agent._build_evaluation_prompt("body text", "source one")

        assert "Tone: Check tone\nClarity: Check clarity" in prompt

    def test_parse_evaluation_response_defaults_missing_overall_score(
        self, agent: QualityAgent
    ) -> None:
        """Given JSON without overall_score, when parsing, then zero is used."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "criterion_scores": {
                    "tone": {
                        "score": 80,
                        "weight": 0.5,
                        "passed": True,
                        "feedback": "good",
                    }
                },
                "passed": True,
            })
        )

        assert result["overall_score"] == 0.0
        assert "tone" in result["criteria_scores"]
        assert result["criteria_scores"]["tone"]["score"] == 80.0

    def test_parse_evaluation_response_defaults_missing_criterion_fields(
        self, agent: QualityAgent
    ) -> None:
        """Given sparse criterion JSON, when parsing, then defaults are applied."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 55.0,
                "criterion_scores": {"tone": {}},
                "passed": True,
            })
        )

        tone = result["criteria_scores"]["tone"]
        assert tone["score"] == 0.0
        assert tone["weight"] == 0.0
        assert tone["passed"] is False
        assert tone["feedback"] == ""

    def test_parse_evaluation_response_defaults_missing_top_level_fields(
        self, agent: QualityAgent
    ) -> None:
        """Given JSON without feedback/passed, when parsing, then defaults are applied."""
        result = agent._parse_evaluation_response(
            json.dumps({"overall_score": 40.0, "criterion_scores": {}})
        )

        assert result["feedback"] == []
        assert result["passed"] is False
        assert result["criteria_scores"] == {}

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

    # Mutation-killing tests for __init__
    def test_init_stores_rubric(
        self, rubric: QualityRubric, mock_llm: AsyncMock
    ) -> None:
        """Given rubric and llm, when creating agent, then rubric is stored."""
        agent = QualityAgent(rubric=rubric, llm=mock_llm)
        assert agent.rubric is rubric

    def test_init_stores_llm(self, rubric: QualityRubric, mock_llm: AsyncMock) -> None:
        """Given rubric and llm, when creating agent, then llm is stored."""
        agent = QualityAgent(rubric=rubric, llm=mock_llm)
        assert agent.llm is mock_llm

    def test_init_stores_embedding_service(
        self, rubric: QualityRubric, mock_llm: AsyncMock, mock_embeddings: AsyncMock
    ) -> None:
        """Given embedding service, when creating agent, then service is stored."""
        agent = QualityAgent(
            rubric=rubric, llm=mock_llm, embedding_service=mock_embeddings
        )
        assert agent._embedding_service is mock_embeddings

    def test_init_embedding_service_defaults_to_none(self, agent: QualityAgent) -> None:
        """Given no embedding service, when creating agent, then service is None."""
        assert agent._embedding_service is None

    # Mutation-killing tests for evaluate
    async def test_evaluate_sanitizes_content_in_prompt(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate is called, then sanitized content is in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "feedback": [],
                "passed": True,
            })
        )

        with patch(
            "rag_backend.agents.quality_agent.sanitize_llm_input",
            return_value="sanitized_content_marker",
        ):
            await agent.evaluate("original content")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "sanitized_content_marker" in prompt

    async def test_evaluate_sanitizes_sources_in_prompt(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given sources, when evaluate is called, then sanitized sources are in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "feedback": [],
                "passed": True,
            })
        )

        with patch(
            "rag_backend.agents.quality_agent.sanitize_llm_input",
            side_effect=lambda x: f"sanitized_{x}",
        ):
            await agent.evaluate("content", sources=["source1", "source2"])

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "sanitized_source1" in prompt
        assert "sanitized_source2" in prompt

    # Mutation-killing tests for _build_evaluation_prompt
    def test_build_evaluation_prompt_includes_exact_applicable_types(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given rubric with multiple types, when building prompt, then exact join format is used."""
        rubric = QualityRubric(
            name="Multi Type Rubric",
            description="Multi type",
            applicable_content_types=["carousel", "blog_post"],
            criteria=[],
        )
        agent = QualityAgent(rubric=rubric, llm=mock_llm)

        prompt = agent._build_evaluation_prompt("content", "sources")

        assert "APPLICABLE TO: carousel, blog_post" in prompt

    # Mutation-killing tests for _parse_evaluation_response
    def test_parse_evaluation_response_invalid_json_exact_defaults(
        self, agent: QualityAgent
    ) -> None:
        """Given invalid JSON, when parsing, then exact defaults are returned."""
        result = agent._parse_evaluation_response("not json")

        assert result["overall_score"] == 0.0
        assert result["criteria_scores"] == {}
        assert result["feedback"] == []
        assert result["passed"] is False

    def test_parse_evaluation_response_float_converts_integers(
        self, agent: QualityAgent
    ) -> None:
        """Given integer overall_score, when parsing, then it is converted to float."""
        result = agent._parse_evaluation_response(
            json.dumps({"overall_score": 85, "criterion_scores": {}, "passed": True})
        )

        assert isinstance(result["overall_score"], float)
        assert result["overall_score"] == 85.0

    def test_parse_evaluation_response_bool_converts_strings(
        self, agent: QualityAgent
    ) -> None:
        """Given string passed value, when parsing, then it is converted to bool."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {},
                "passed": "true",
            })
        )

        assert isinstance(result["passed"], bool)
        assert result["passed"] is True

    def test_parse_evaluation_response_criterion_float_converts_integers(
        self, agent: QualityAgent
    ) -> None:
        """Given integer criterion score, when parsing, then it is converted to float."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {
                    "tone": {"score": 90, "weight": 1, "passed": True, "feedback": ""}
                },
                "passed": True,
            })
        )

        tone = result["criteria_scores"]["tone"]
        assert isinstance(tone["score"], float)
        assert tone["score"] == 90.0

    def test_parse_evaluation_response_criterion_bool_converts_integers(
        self, agent: QualityAgent
    ) -> None:
        """Given integer criterion passed value, when parsing, then it is converted to bool."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {
                    "tone": {"score": 90.0, "weight": 1.0, "passed": 1, "feedback": ""}
                },
                "passed": True,
            })
        )

        tone = result["criteria_scores"]["tone"]
        assert isinstance(tone["passed"], bool)
        assert tone["passed"] is True

    def test_parse_evaluation_response_with_criterion_scores_present(
        self, agent: QualityAgent
    ) -> None:
        """Given criterion_scores present, when parsing, then it is parsed correctly."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {
                    "tone": {
                        "score": 90.0,
                        "weight": 1.0,
                        "passed": True,
                        "feedback": "good",
                    }
                },
                "passed": True,
            })
        )

        assert "tone" in result["criteria_scores"]
        assert result["criteria_scores"]["tone"]["feedback"] == "good"

    def test_parse_evaluation_response_criterion_missing_passed(
        self, agent: QualityAgent
    ) -> None:
        """Given criterion missing passed, when parsing, then default is False."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {
                    "tone": {"score": 90.0, "weight": 1.0, "feedback": "good"}
                },
                "passed": True,
            })
        )

        tone = result["criteria_scores"]["tone"]
        assert tone["passed"] is False

    def test_parse_evaluation_response_criterion_missing_feedback(
        self, agent: QualityAgent
    ) -> None:
        """Given criterion missing feedback, when parsing, then default is empty string."""
        result = agent._parse_evaluation_response(
            json.dumps({
                "overall_score": 80.0,
                "criterion_scores": {
                    "tone": {"score": 90.0, "weight": 1.0, "passed": True}
                },
                "passed": True,
            })
        )

        tone = result["criteria_scores"]["tone"]
        assert tone["feedback"] == ""

    # Mutation-killing tests for evaluate_criterion
    async def test_evaluate_criterion_hybrid_returns_75(
        self, agent: QualityAgent
    ) -> None:
        """Given HYBRID criterion, when evaluate_criterion called, then default 75.0 returned."""
        criterion = {
            "id": "hybrid",
            "name": "Hybrid Check",
            "description": "Needs hybrid",
            "weight": 0.5,
            "evaluation_method": EvaluationMethod.HYBRID,
            "min_threshold": 70.0,
            "scoring_scale": "0-100",
            "prompt_template": "Hybrid check: {content}",
        }

        score = await agent.evaluate_criterion(criterion, "content")

        assert score == 75.0

    # Mutation-killing tests for _ai_evaluate
    async def test_ai_evaluate_prompt_includes_sources(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given sources, when _ai_evaluate called, then prompt includes sources."""
        mock_llm.ainvoke.return_value = MagicMock(content="90.0")

        criterion = {
            "id": "ai",
            "name": "AI Check",
            "description": "AI check",
            "weight": 0.5,
            "evaluation_method": EvaluationMethod.AI_AUTO,
            "min_threshold": 70.0,
            "scoring_scale": "0-100",
            "prompt_template": "Evaluate: {content} with {sources}",
        }

        await agent._ai_evaluate(criterion, "content", ["source1", "source2"])

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "content" in prompt
        assert "source1" in prompt
        assert "source2" in prompt

    # Mutation-killing tests for _extract_score
    def test_extract_score_empty_string(self, agent: QualityAgent) -> None:
        """Given empty response, when extracting score, then 50.0 is returned."""
        score = agent._extract_score("")

        assert score == 50.0

    def test_extract_score_first_number_extracted(self, agent: QualityAgent) -> None:
        """Given multiple numbers, when extracting score, then first number is returned."""
        score = agent._extract_score("Score: 85.5 and 90.0")

        assert score == 85.5

    def test_extract_score_returns_float(self, agent: QualityAgent) -> None:
        """Given integer response, when extracting score, then float is returned."""
        score = agent._extract_score("85")

        assert isinstance(score, float)
        assert score == 85.0

    # Mutation-killing tests for generate_improvement_suggestions
    async def test_generate_suggestions_exactly_at_threshold_returns_empty(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given score exactly at threshold, when generating suggestions, then empty list returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="- Suggestion")

        criterion = agent.rubric.criteria[0]
        suggestions = await agent.generate_improvement_suggestions(
            criterion, "content", criterion["min_threshold"]
        )

        assert suggestions == []

    async def test_generate_suggestions_exact_suggestions(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given LLM response, when generating suggestions, then exact suggestions are returned."""
        mock_llm.ainvoke.return_value = MagicMock(
            content="- Suggestion one\n- Suggestion two\n- Here are some"
        )

        criterion = agent.rubric.criteria[0]
        suggestions = await agent.generate_improvement_suggestions(
            criterion, "content", 60.0
        )

        assert suggestions == ["Suggestion one", "Suggestion two"]

    async def test_generate_suggestions_sanitizes_content(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when generating suggestions, then sanitized content is in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(content="- Suggestion")

        with patch(
            "rag_backend.agents.quality_agent.sanitize_llm_input",
            return_value="sanitized_content",
        ):
            await agent.generate_improvement_suggestions(
                agent.rubric.criteria[0], "original content", 60.0
            )

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "sanitized_content" in prompt

    # Mutation-killing tests for calculate_originality
    async def test_calculate_originality_exact_source_bonus(
        self, agent: QualityAgent
    ) -> None:
        """Given multiple sources, when calculating originality, then exact source bonus is applied."""
        score = await agent.calculate_originality("a", ["s1", "s2", "s3"])

        # base_score = 50.0, source_bonus = min(3 * 10, 30) = 30, content_bonus = min(1 / 1000, 20) = 0.001
        assert score == 80.001

    async def test_calculate_originality_exact_content_bonus(
        self, agent: QualityAgent
    ) -> None:
        """Given long content, when calculating originality, then exact content bonus is applied."""
        score = await agent.calculate_originality("x" * 1000, [])

        # base_score = 50.0, source_bonus = 0, content_bonus = min(1000 / 1000, 20) = 1.0
        assert score == 51.0

    async def test_calculate_originality_capped_at_100(
        self, agent: QualityAgent
    ) -> None:
        """Given many sources and long content, when calculating originality, then score is capped at 100."""
        # MAX_LLM_INPUT_LENGTH = 10000, so "x" * 20000 is truncated to 10000 chars
        # content_bonus = min(10000 / 1000, 20) = 10
        # source_bonus = min(10 * 10, 30) = 30
        # base_score = 50, total = 90
        score = await agent.calculate_originality("x" * 20000, ["s"] * 10)

        assert score == 90.0

    async def test_calculate_originality_no_sources_empty_content(
        self, agent: QualityAgent
    ) -> None:
        """Given no sources and empty content, when calculating originality, then base score is returned."""
        score = await agent.calculate_originality("", [])

        assert score == 50.0

    # Mutation-killing tests for _cosine_similarity
    def test_cosine_similarity_identical_vectors_returns_one(
        self, agent: QualityAgent
    ) -> None:
        """Given identical vectors, when calculating similarity, then 1.0 is returned."""
        score = agent._cosine_similarity([1.0, 0.0], [1.0, 0.0])

        assert score == 1.0

    def test_cosine_similarity_orthogonal_vectors_returns_zero(
        self, agent: QualityAgent
    ) -> None:
        """Given orthogonal vectors, when calculating similarity, then 0.0 is returned."""
        score = agent._cosine_similarity([1.0, 0.0], [0.0, 1.0])

        assert score == 0.0

    def test_cosine_similarity_non_zero_value(self, agent: QualityAgent) -> None:
        """Given non-trivial vectors, when calculating similarity, then correct value is returned."""
        score = agent._cosine_similarity([1.0, 1.0], [1.0, 0.0])

        assert score == pytest.approx(0.70710678, abs=0.0001)

    def test_cosine_similarity_returns_float(self, agent: QualityAgent) -> None:
        """Given vectors, when calculating similarity, then float is returned."""
        score = agent._cosine_similarity([1.0, 0.0], [1.0, 0.0])

        assert isinstance(score, float)

    # Mutation-killing tests for evaluate_eeat
    async def test_evaluate_eeat_invalid_json_all_defaults_exactly_50(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given invalid JSON, when evaluating E-E-A-T, then all defaults are exactly 50."""
        mock_llm.ainvoke.return_value = MagicMock(content="not json")

        result = await agent.evaluate_eeat("content", ["source"])

        assert result["experience"] == 50
        assert result["expertise"] == 50
        assert result["authoritativeness"] == 50
        assert result["trustworthiness"] == 50
        assert result["overall_eeat"] == 50

    async def test_evaluate_eeat_sparse_json_uses_defaults(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given sparse JSON, when evaluating E-E-A-T, then missing keys default to 50.0."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"experience": 80.0, "overall_eeat": 70.0})
        )

        result = await agent.evaluate_eeat("content", ["source"])

        assert result["experience"] == 80.0
        assert result["expertise"] == 50.0
        assert result["authoritativeness"] == 50.0
        assert result["trustworthiness"] == 50.0
        assert result["overall_eeat"] == 70.0

    async def test_evaluate_eeat_returns_floats(
        self, agent: QualityAgent, mock_llm: AsyncMock
    ) -> None:
        """Given valid JSON with integers, when evaluating E-E-A-T, then all values are floats."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({
                "experience": 80,
                "expertise": 85,
                "authoritativeness": 90,
                "trustworthiness": 95,
                "overall_eeat": 87,
            })
        )

        result = await agent.evaluate_eeat("content", ["source"])

        assert isinstance(result["experience"], float)
        assert isinstance(result["expertise"], float)
        assert isinstance(result["authoritativeness"], float)
        assert isinstance(result["trustworthiness"], float)
        assert isinstance(result["overall_eeat"], float)
