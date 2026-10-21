"""Assertion-bearing tests that pin exact PersonaAgent behaviour.

Feature: Persona voice enforcement and scoring
"""

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.domain.models.persona import PersonaProfile, ToneAttributes


@pytest.fixture
def mock_llm() -> AsyncMock:
    """An LLM returning a fixed rewrite."""
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(content="rewritten")
    return llm


def _agent(persona: PersonaProfile, llm: AsyncMock) -> PersonaAgent:
    """A persona agent over the given persona."""
    return PersonaAgent(persona=persona, llm=llm)


@pytest.fixture
def rich_persona() -> PersonaProfile:
    """A persona with several phrases and samples and only a formal tone."""
    return PersonaProfile(
        name="Voice",
        tone_attributes=cast(ToneAttributes, {"formal": 0.3}),
        forbidden_phrases=["bad one", "bad two"],
        preferred_phrases=["good one", "good two"],
        writing_samples=["sample one", "sample two"],
        expertise_areas=["testing"],
    )


# Scenario: Enforce without a context sends an empty context
async def test_enforce_default_context_is_empty(
    rich_persona: PersonaProfile, mock_llm: AsyncMock
) -> None:
    """Omitting the context renders an empty CONTEXT line."""
    await _agent(rich_persona, mock_llm).enforce("body")

    prompt = mock_llm.ainvoke.call_args[0][0][0].content
    assert "\n\nCONTEXT: \n\nCONTENT TO REWRITE:\nbody" in prompt


# Scenario: The style guide lists phrases and samples one per line
def test_style_guide_joins_lists_with_newlines(
    rich_persona: PersonaProfile, mock_llm: AsyncMock
) -> None:
    """Forbidden, preferred and sample lists are newline-joined bullets."""
    guide = _agent(rich_persona, mock_llm).style_guide()

    assert "FORBIDDEN PHRASES: - bad one\n- bad two" in guide
    assert "PREFERRED PHRASES: - good one\n- good two" in guide
    assert "WRITING SAMPLES: - sample one\n- sample two" in guide


# Scenario: Missing tone attributes default to 0.5
def test_style_guide_missing_tones_default_to_half(
    rich_persona: PersonaProfile, mock_llm: AsyncMock
) -> None:
    """Conversational and humorous tones default to 0.5 when absent."""
    guide = _agent(rich_persona, mock_llm).style_guide()

    assert "TONE: formal=0.3, conversational=0.5, humorous=0.5" in guide


# Scenario: A sub-score of exactly 10 still marks a 0-10 answer
def test_scores_with_a_ten_are_scaled(
    rich_persona: PersonaProfile, mock_llm: AsyncMock
) -> None:
    """A response whose highest score is exactly 10 is scaled to 0-100."""
    payload = {
        "tone_match": 10,
        "sentence_structure_match": 5,
        "opinion_strength": 5,
        "originality": 5,
        "human_authenticity": 5,
        "overall": 8,
    }

    result = _agent(rich_persona, mock_llm)._parse_evaluation_response(
        json.dumps(payload)
    )

    assert result["tone_match"] == 100.0
    assert result["sentence_structure_match"] == 50.0
    assert result["overall"] == 80.0
