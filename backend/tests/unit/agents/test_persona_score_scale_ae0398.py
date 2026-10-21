"""Voice scores are on 0-100.

Gherkin: tests/features/persona_score_scale_ae0398.feature
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.models.persona import PersonaProfile

pytestmark = pytest.mark.unit

_FIELDS = (
    "tone_match",
    "sentence_structure_match",
    "opinion_strength",
    "originality",
    "human_authenticity",
    "overall",
)


async def _evaluate(answer: str) -> dict[str, object]:
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(content=answer)
    agent = PersonaAgent(persona=PersonaProfile(name="Pedro"), llm=llm)
    return await agent.evaluate_match("Meu time de agentes não é um chatbot.")


def _answer(**scores: float) -> str:
    return json.dumps({**scores, "suggestions": ["Adicione um número."]})


# Scenario: A 0-10 answer is scaled to 0-100
async def test_ten_point_answer_is_scaled() -> None:
    result = await _evaluate(
        _answer(
            tone_match=9.0,
            sentence_structure_match=9.5,
            opinion_strength=8.0,
            originality=7.0,
            human_authenticity=8.5,
            overall=8.5,
        )
    )
    assert result["overall"] == 85.0
    assert result["sentence_structure_match"] == 95.0
    assert result["suggestions"] == ["Adicione um número."]


# Scenario: A 0-100 answer is kept as is
async def test_hundred_point_answer_is_unchanged() -> None:
    result = await _evaluate(
        _answer(
            tone_match=90.0,
            sentence_structure_match=80.0,
            opinion_strength=75.0,
            originality=70.0,
            human_authenticity=88.0,
            overall=82.0,
        )
    )
    assert result["overall"] == 82.0
    assert result["tone_match"] == 90.0


# Scenario: An all-zero or unreadable answer stays at 0
@pytest.mark.parametrize("answer", [_answer(**dict.fromkeys(_FIELDS, 0.0)), "not json"])
async def test_zero_or_unreadable_answer_stays_zero(answer: str) -> None:
    result = await _evaluate(answer)
    assert all(result[field] == 0.0 for field in _FIELDS)


# Scenario: On-voice copy passes the voice floor
async def test_on_voice_ten_point_answer_passes_the_floor() -> None:
    result = await _evaluate(_answer(**dict.fromkeys(_FIELDS, 8.2)))
    overall = result["overall"]
    assert isinstance(overall, float)
    assert overall >= VOICE_MATCH_MIN_SCORE
