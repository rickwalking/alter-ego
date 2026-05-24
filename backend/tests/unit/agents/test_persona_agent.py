"""Unit tests for PersonaAgent.

Feature: Persona voice enforcement and scoring
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.domain.models.persona import PersonaProfile


class TestPersonaAgent:
    """Tests for PersonaAgent."""

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        """Create a mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def persona(self) -> PersonaProfile:
        """Create a test persona."""
        return PersonaProfile(
            name="Test Voice",
            description="Test persona for unit tests",
            tone_attributes={"formal": 0.3, "conversational": 0.8, "humorous": 0.4},
            forbidden_phrases=["bad phrase"],
            preferred_phrases=["good phrase"],
            writing_samples=["sample 1", "sample 2"],
            expertise_areas=["testing"],
        )

    @pytest.fixture
    def agent(self, persona: PersonaProfile, mock_llm: AsyncMock) -> PersonaAgent:
        """Create a PersonaAgent instance."""
        return PersonaAgent(persona=persona, llm=mock_llm)

    # Scenario: Enforce persona voice on content
    async def test_enforce_rewrites_content(self, agent: PersonaAgent, mock_llm: AsyncMock) -> None:
        """Given content, when enforce is called, then rewritten content is returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten text")

        result = await agent.enforce("original content")

        assert result == "rewritten text"
        mock_llm.ainvoke.assert_called_once()

    async def test_enforce_includes_context(self, agent: PersonaAgent, mock_llm: AsyncMock) -> None:
        """Given content and context, when enforce is called, then context is included in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten")

        await agent.enforce("content", context="test context")

        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "test context" in call_args[0].content

    # Scenario: Evaluate voice match
    async def test_evaluate_match_parses_json_response(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate_match is called, then scores are parsed from JSON."""
        response_data = {
            "tone_match": 85.0,
            "sentence_structure_match": 90.0,
            "opinion_strength": 75.0,
            "originality": 80.0,
            "human_authenticity": 95.0,
            "overall": 85.0,
            "suggestions": ["suggestion 1"],
        }
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(response_data))

        result = await agent.evaluate_match("test content")

        assert result["tone_match"] == 85.0
        assert result["overall"] == 85.0
        assert result["suggestions"] == ["suggestion 1"]

    async def test_evaluate_match_handles_invalid_json(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given invalid JSON response, when evaluate_match is called, then defaults returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="not json")

        result = await agent.evaluate_match("test content")

        assert result["overall"] == 0.0
        assert result["suggestions"] == []

    async def test_evaluate_match_handles_missing_keys(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given JSON missing keys, when evaluate_match called, then missing default to 0."""
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps({"tone_match": 50.0}))

        result = await agent.evaluate_match("test content")

        assert result["tone_match"] == 50.0
        assert result["overall"] == 0.0

    # Scenario: Build style guide
    def test_build_style_guide_includes_persona_name(self, agent: PersonaAgent) -> None:
        """Given persona, when building style guide, then persona name is included."""
        guide = agent._build_style_guide()

        assert "Test Voice" in guide

    def test_build_style_guide_includes_forbidden_phrases(self, agent: PersonaAgent) -> None:
        """Given persona with forbidden phrases, when building style guide, phrases included."""
        guide = agent._build_style_guide()

        assert "bad phrase" in guide

    def test_build_style_guide_includes_preferred_phrases(self, agent: PersonaAgent) -> None:
        """Given persona with preferred phrases, when building style guide, phrases included."""
        guide = agent._build_style_guide()

        assert "good phrase" in guide

    def test_build_style_guide_includes_expertise(self, agent: PersonaAgent) -> None:
        """Given persona with expertise areas, when building style guide, then areas included."""
        guide = agent._build_style_guide()

        assert "testing" in guide

    # Scenario: Parse evaluation response
    def test_parse_evaluation_response_with_valid_json(self, agent: PersonaAgent) -> None:
        """Given valid JSON, when parsing, then scores are extracted."""
        response = json.dumps(
            {
                "tone_match": 80.0,
                "sentence_structure_match": 85.0,
                "opinion_strength": 70.0,
                "originality": 90.0,
                "human_authenticity": 95.0,
                "overall": 84.0,
                "suggestions": ["improve"],
            }
        )

        result = agent._parse_evaluation_response(response)

        assert result["overall"] == 84.0
        assert result["suggestions"] == ["improve"]

    def test_parse_evaluation_response_with_invalid_json(self, agent: PersonaAgent) -> None:
        """Given invalid JSON, when parsing, then default scores are returned."""
        result = agent._parse_evaluation_response("not json")

        assert result["overall"] == 0.0
        assert result["suggestions"] == []

    # Scenario: Handle empty persona attributes
    def test_build_style_guide_with_empty_phrases(self, mock_llm: AsyncMock) -> None:
        """Given persona with no phrases, when building style guide, then 'None' is shown."""
        persona = PersonaProfile(
            name="Empty Persona",
            forbidden_phrases=[],
            preferred_phrases=[],
            writing_samples=[],
            expertise_areas=[],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "None" in guide

    # Scenario: Handle LLM errors
    async def test_enforce_propagates_llm_errors(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given LLM raises error, when enforce is called, then error is propagated."""
        mock_llm.ainvoke.side_effect = Exception("LLM error")

        with pytest.raises(Exception, match="LLM error"):
            await agent.enforce("content")

    async def test_evaluate_match_propagates_llm_errors(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given LLM raises error, when evaluate_match is called, then error is propagated."""
        mock_llm.ainvoke.side_effect = Exception("LLM error")

        with pytest.raises(Exception, match="LLM error"):
            await agent.evaluate_match("content")
