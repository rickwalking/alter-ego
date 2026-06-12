"""Unit tests for PersonaAgent.

Feature: Persona voice enforcement and scoring
"""

import json
from inspect import signature
from unittest.mock import AsyncMock, MagicMock, patch

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
    async def test_enforce_rewrites_content(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when enforce is called, then rewritten content is returned."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten text")

        result = await agent.enforce("original content")

        assert result == "rewritten text"
        mock_llm.ainvoke.assert_called_once()

    async def test_enforce_prompt_includes_style_guide_and_content(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content without context, when enforce is called, then prompt is complete."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten text")

        await agent.enforce("original content")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "Test Voice" in prompt
        assert "bad phrase" in prompt
        assert "good phrase" in prompt
        assert "CONTENT TO REWRITE:\noriginal content" in prompt
        context_value = prompt.split("CONTEXT: ", 1)[1].split(
            "\n\nCONTENT TO REWRITE:", 1
        )[0]
        assert context_value.strip() == ""

    def test_enforce_default_context_parameter_is_empty(
        self, agent: PersonaAgent
    ) -> None:
        """Given PersonaAgent, when inspecting enforce, then context default is empty."""
        assert signature(agent.enforce).parameters["context"].default == ""

    async def test_enforce_passes_langfuse_callbacks(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given enforce call, when invoking LLM, then Langfuse callbacks are attached."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten text")
        handler = MagicMock()

        with patch(
            "rag_backend.agents.persona_agent.get_langfuse_runnable_config",
            return_value={"callbacks": [handler]},
        ) as mock_config:
            await agent.enforce("original content")

        mock_config.assert_called_once()
        assert mock_llm.ainvoke.call_args.args[1] == {"callbacks": [handler]}

    async def test_enforce_includes_context(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
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

    async def test_evaluate_match_prompt_includes_content_and_style_guide(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate_match is called, then prompt includes rubric details."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"overall": 80.0, "suggestions": []})
        )

        await agent.evaluate_match("unique eval content xyz")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "unique eval content xyz" in prompt
        assert "Test Voice" in prompt
        assert "tone_match" in prompt

    async def test_evaluate_match_passes_langfuse_callbacks(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given evaluate_match call, when invoking LLM, then Langfuse callbacks are attached."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"overall": 80.0, "suggestions": []})
        )
        handler = MagicMock()

        with patch(
            "rag_backend.agents.persona_agent.get_langfuse_runnable_config",
            return_value={"callbacks": [handler]},
        ) as mock_config:
            await agent.evaluate_match("content")

        mock_config.assert_called_once()
        assert mock_llm.ainvoke.call_args.args[1] == {"callbacks": [handler]}

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
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"tone_match": 50.0})
        )

        result = await agent.evaluate_match("test content")

        assert result["tone_match"] == 50.0
        assert result["overall"] == 0.0

    # Scenario: Build style guide
    def test_build_style_guide_includes_persona_name(self, agent: PersonaAgent) -> None:
        """Given persona, when building style guide, then persona name is included."""
        guide = agent._build_style_guide()

        assert "Test Voice" in guide

    def test_build_style_guide_includes_forbidden_phrases(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona with forbidden phrases, when building style guide, phrases included."""
        guide = agent._build_style_guide()

        assert "bad phrase" in guide

    def test_build_style_guide_includes_preferred_phrases(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona with preferred phrases, when building style guide, phrases included."""
        guide = agent._build_style_guide()

        assert "good phrase" in guide

    def test_build_style_guide_includes_expertise(self, agent: PersonaAgent) -> None:
        """Given persona with expertise areas, when building style guide, then areas included."""
        guide = agent._build_style_guide()

        assert "testing" in guide

    def test_build_style_guide_includes_tone_attributes(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona tone attributes, when building style guide, then values appear."""
        guide = agent._build_style_guide()

        assert "formal=0.3" in guide
        assert "conversational=0.8" in guide
        assert "humorous=0.4" in guide

    # Scenario: Parse evaluation response
    def test_parse_evaluation_response_with_valid_json(
        self, agent: PersonaAgent
    ) -> None:
        """Given valid JSON, when parsing, then scores are extracted."""
        response = json.dumps({
            "tone_match": 80.0,
            "sentence_structure_match": 85.0,
            "opinion_strength": 70.0,
            "originality": 90.0,
            "human_authenticity": 95.0,
            "overall": 84.0,
            "suggestions": ["improve"],
        })

        result = agent._parse_evaluation_response(response)

        assert result["overall"] == 84.0
        assert result["suggestions"] == ["improve"]

    def test_parse_evaluation_response_preserves_all_score_fields(
        self, agent: PersonaAgent
    ) -> None:
        """Given full JSON payload, when parsing, then every score field is preserved."""
        response = json.dumps({
            "tone_match": 80.0,
            "sentence_structure_match": 85.0,
            "opinion_strength": 70.0,
            "originality": 90.0,
            "human_authenticity": 95.0,
            "overall": 84.0,
            "suggestions": ["improve"],
        })

        result = agent._parse_evaluation_response(response)

        assert result["tone_match"] == 80.0
        assert result["sentence_structure_match"] == 85.0
        assert result["opinion_strength"] == 70.0
        assert result["originality"] == 90.0
        assert result["human_authenticity"] == 95.0

    def test_parse_evaluation_response_with_invalid_json(
        self, agent: PersonaAgent
    ) -> None:
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

    # Scenario: __init__ stores dependencies correctly
    def test_init_stores_persona_and_llm(
        self, persona: PersonaProfile, mock_llm: AsyncMock
    ) -> None:
        """Given persona and llm, when initializing, then both are stored exactly."""
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        assert agent.persona is persona
        assert agent.llm is mock_llm

    # Scenario: enforce sanitizes inputs and builds exact prompt
    async def test_enforce_sanitizes_content(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given raw content, when enforce is called, then sanitized content is in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten")

        with patch(
            "rag_backend.agents.persona_agent.sanitize_llm_input",
            side_effect=lambda x: f"sanitized_{x}",
        ):
            await agent.enforce("raw")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "sanitized_raw" in prompt

    async def test_enforce_sanitizes_context(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given context, when enforce is called, then sanitized context is in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten")

        with patch(
            "rag_backend.agents.persona_agent.sanitize_llm_input",
            side_effect=lambda x: f"sanitized_{x}",
        ):
            await agent.enforce("content", context="ctx")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "sanitized_ctx" in prompt

    async def test_enforce_prompt_exact_format(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content and context, when enforce is called, then prompt matches exact format."""
        mock_llm.ainvoke.return_value = MagicMock(content="rewritten")

        await agent.enforce("mycontent", context="mycontext")

        style_guide = agent._build_style_guide()
        expected = (
            f"{style_guide}\n\nCONTEXT: mycontext\n\nCONTENT TO REWRITE:\nmycontent"
        )
        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert prompt == expected

    # Scenario: evaluate_match sanitizes inputs and builds exact prompt
    async def test_evaluate_match_sanitizes_content(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given raw content, when evaluate_match is called, then sanitized content is in prompt."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"overall": 80.0, "suggestions": []})
        )

        with patch(
            "rag_backend.agents.persona_agent.sanitize_llm_input",
            side_effect=lambda x: f"sanitized_{x}",
        ):
            await agent.evaluate_match("raw")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "sanitized_raw" in prompt

    async def test_evaluate_match_prompt_exact_format(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate_match is called, then prompt matches exact format."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"overall": 80.0, "suggestions": []})
        )

        await agent.evaluate_match("mycontent")

        style_guide = agent._build_style_guide()
        expected = (
            f"{style_guide}\n\n"
            "Score this content on how well it matches the persona above.\n\n"
            "CONTENT:\nmycontent\n\n"
            "Respond with JSON containing: tone_match, sentence_structure_match, "
            "opinion_strength, originality, human_authenticity, overall, suggestions."
        )
        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert prompt == expected

    async def test_evaluate_match_prompt_includes_all_json_keys(
        self, agent: PersonaAgent, mock_llm: AsyncMock
    ) -> None:
        """Given content, when evaluate_match is called, then prompt lists all required JSON keys."""
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"overall": 80.0, "suggestions": []})
        )

        await agent.evaluate_match("content")

        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        assert "tone_match" in prompt
        assert "sentence_structure_match" in prompt
        assert "opinion_strength" in prompt
        assert "originality" in prompt
        assert "human_authenticity" in prompt
        assert "overall" in prompt
        assert "suggestions" in prompt

    # Scenario: _parse_evaluation_response kills default and key mutants
    def test_parse_evaluation_response_empty_dict_returns_all_defaults(
        self, agent: PersonaAgent
    ) -> None:
        """Given empty JSON object, when parsing, then all defaults are exactly 0.0 and empty list."""
        result = agent._parse_evaluation_response("{}")

        assert result["tone_match"] == 0.0
        assert result["sentence_structure_match"] == 0.0
        assert result["opinion_strength"] == 0.0
        assert result["originality"] == 0.0
        assert result["human_authenticity"] == 0.0
        assert result["overall"] == 0.0
        assert result["suggestions"] == []

    def test_parse_evaluation_response_with_integers(self, agent: PersonaAgent) -> None:
        """Given integer scores in JSON, when parsing, then values are converted to floats."""
        response = json.dumps({
            "tone_match": 85,
            "sentence_structure_match": 90,
            "opinion_strength": 75,
            "originality": 80,
            "human_authenticity": 95,
            "overall": 85,
            "suggestions": ["suggestion"],
        })

        result = agent._parse_evaluation_response(response)

        assert isinstance(result["tone_match"], float)
        assert result["tone_match"] == 85.0
        assert isinstance(result["overall"], float)
        assert result["overall"] == 85.0

    def test_parse_evaluation_response_with_string_numbers(
        self, agent: PersonaAgent
    ) -> None:
        """Given string numbers in JSON, when parsing, then values are converted to floats."""
        response = json.dumps({
            "tone_match": "85.5",
            "sentence_structure_match": "90.0",
            "opinion_strength": "75.0",
            "originality": "80.0",
            "human_authenticity": "95.0",
            "overall": "85.0",
            "suggestions": [],
        })

        result = agent._parse_evaluation_response(response)

        assert isinstance(result["tone_match"], float)
        assert result["tone_match"] == 85.5

    def test_parse_evaluation_response_with_wrong_keys(
        self, agent: PersonaAgent
    ) -> None:
        """Given JSON with wrong keys, when parsing, then all defaults are returned."""
        response = json.dumps({
            "tone": 85,
            "match": 90,
            "opinion": 75,
            "original": 80,
            "human": 95,
            "total": 85,
            "suggest": ["suggestion"],
        })

        result = agent._parse_evaluation_response(response)

        assert result["tone_match"] == 0.0
        assert result["sentence_structure_match"] == 0.0
        assert result["opinion_strength"] == 0.0
        assert result["originality"] == 0.0
        assert result["human_authenticity"] == 0.0
        assert result["overall"] == 0.0
        assert result["suggestions"] == []

    def test_parse_evaluation_response_with_partial_keys(
        self, agent: PersonaAgent
    ) -> None:
        """Given JSON with only some keys, when parsing, then missing keys default to 0.0."""
        response = json.dumps({
            "tone_match": 50,
            "overall": 60,
        })

        result = agent._parse_evaluation_response(response)

        assert result["tone_match"] == 50.0
        assert result["overall"] == 60.0
        assert result["sentence_structure_match"] == 0.0
        assert result["opinion_strength"] == 0.0
        assert result["originality"] == 0.0
        assert result["human_authenticity"] == 0.0
        assert result["suggestions"] == []

    def test_parse_evaluation_response_returns_exact_float_types(
        self, agent: PersonaAgent
    ) -> None:
        """Given valid JSON, when parsing, then every score field is a float."""
        response = json.dumps({
            "tone_match": 80.0,
            "sentence_structure_match": 85.0,
            "opinion_strength": 70.0,
            "originality": 90.0,
            "human_authenticity": 95.0,
            "overall": 84.0,
            "suggestions": [],
        })

        result = agent._parse_evaluation_response(response)

        assert isinstance(result["tone_match"], float)
        assert isinstance(result["sentence_structure_match"], float)
        assert isinstance(result["opinion_strength"], float)
        assert isinstance(result["originality"], float)
        assert isinstance(result["human_authenticity"], float)
        assert isinstance(result["overall"], float)

    # Scenario: _build_style_guide kills slicing, formatting, and default mutants
    def test_build_style_guide_with_six_samples_shows_only_first_five(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given six writing samples, when building style guide, then only first five appear."""
        persona = PersonaProfile(
            name="Sample Persona",
            writing_samples=["s1", "s2", "s3", "s4", "s5", "s6"],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "- s1" in guide
        assert "- s2" in guide
        assert "- s3" in guide
        assert "- s4" in guide
        assert "- s5" in guide
        assert "- s6" not in guide

    def test_build_style_guide_with_missing_tone_attribute_uses_default(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given tone_attributes missing formal key, when building style guide, then default 0.5 is used."""
        persona = PersonaProfile(
            name="Tone Persona",
            tone_attributes={"conversational": 0.8, "humorous": 0.4},
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "formal=0.5" in guide

    def test_build_style_guide_with_empty_forbidden_shows_none(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given empty forbidden phrases, when building style guide, then 'None' is shown."""
        persona = PersonaProfile(
            name="Empty Persona",
            forbidden_phrases=[],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "FORBIDDEN PHRASES: None" in guide

    def test_build_style_guide_with_empty_preferred_shows_none(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given empty preferred phrases, when building style guide, then 'None' is shown."""
        persona = PersonaProfile(
            name="Empty Persona",
            preferred_phrases=[],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "PREFERRED PHRASES: None" in guide

    def test_build_style_guide_with_empty_samples_shows_none(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given empty writing samples, when building style guide, then 'None' is shown."""
        persona = PersonaProfile(
            name="Empty Persona",
            writing_samples=[],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "WRITING SAMPLES: None" in guide

    def test_build_style_guide_with_empty_expertise_shows_empty_string(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given empty expertise areas, when building style guide, then empty string is shown."""
        persona = PersonaProfile(
            name="Empty Persona",
            expertise_areas=[],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "EXPERTISE AREAS: \n" in guide

    def test_build_style_guide_with_zero_tone(self, mock_llm: AsyncMock) -> None:
        """Given tone value of 0.0, when building style guide, then zero appears."""
        persona = PersonaProfile(
            name="Tone Persona",
            tone_attributes={"formal": 0.0, "conversational": 0.0, "humorous": 0.0},
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "formal=0.0" in guide
        assert "conversational=0.0" in guide
        assert "humorous=0.0" in guide

    def test_build_style_guide_with_one_tone(self, mock_llm: AsyncMock) -> None:
        """Given tone value of 1.0, when building style guide, then one appears."""
        persona = PersonaProfile(
            name="Tone Persona",
            tone_attributes={"formal": 1.0, "conversational": 1.0, "humorous": 1.0},
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "formal=1.0" in guide
        assert "conversational=1.0" in guide
        assert "humorous=1.0" in guide

    def test_build_style_guide_includes_sentence_structure_preferences(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona, when building style guide, then sentence structure preferences are included."""
        guide = agent._build_style_guide()

        assert "Short punchy sentences. Occasional longer ones for rhythm." in guide

    def test_build_style_guide_includes_paragraph_style(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona, when building style guide, then paragraph style is included."""
        guide = agent._build_style_guide()

        assert "1-3 sentences per paragraph. White space is key." in guide

    def test_build_style_guide_includes_opinion_expression(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona, when building style guide, then opinion expression is included."""
        guide = agent._build_style_guide()

        assert "Strong opinions, loosely held. Never neutral." in guide

    def test_build_style_guide_forbidden_phrase_format(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona with forbidden phrases, when building style guide, then phrases are prefixed with dash."""
        guide = agent._build_style_guide()

        assert "- bad phrase" in guide

    def test_build_style_guide_preferred_phrase_format(
        self, agent: PersonaAgent
    ) -> None:
        """Given persona with preferred phrases, when building style guide, then phrases are prefixed with dash."""
        guide = agent._build_style_guide()

        assert "- good phrase" in guide

    def test_build_style_guide_sample_format(self, agent: PersonaAgent) -> None:
        """Given persona with writing samples, when building style guide, then samples are prefixed with dash."""
        guide = agent._build_style_guide()

        assert "- sample 1" in guide
        assert "- sample 2" in guide

    def test_build_style_guide_expertise_joined_with_comma_space(
        self, mock_llm: AsyncMock
    ) -> None:
        """Given persona with multiple expertise areas, when building style guide, then areas are joined with comma and space."""
        persona = PersonaProfile(
            name="Multi Expert",
            expertise_areas=["ai", "ml", "security"],
        )
        agent = PersonaAgent(persona=persona, llm=mock_llm)

        guide = agent._build_style_guide()

        assert "ai, ml, security" in guide
