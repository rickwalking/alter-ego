"""The POV outline carries the project's persona (PR #106 review, item 3).

Gherkin: tests/features/carousel_pov_prompts.feature ("Persona context")
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.pov_persona_context import pov_persona_context
from rag_backend.domain.constants.pov_prompts import NO_PERSONA_CONTEXT
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.models.pov_prompts import PovOutlineRequest, PovThesis
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache

_ROLES = ("hook", "thesis", "point", "cta")


def _pedro() -> PersonaProfile:
    return PersonaProfile(
        name="Pedro",
        description="Direto, técnico, sem rodeios.",
        opinion_expression="Opinião forte, dita na primeira frase.",
        preferred_phrases=["Quem decide ainda é você."],
        forbidden_phrases=["no mundo de hoje", "revolucionário"],
    )


def _request(persona: PersonaProfile | None) -> PovOutlineRequest:
    return PovOutlineRequest(
        topic="Julgamento técnico",
        audience="Devs",
        brief="b",
        pov=PovThesis(
            thesis="A IA escreve código; decidir é seu.", pov_format="opiniao"
        ),
        roles=_ROLES,
        persona=persona,
    )


@pytest.mark.unit
class TestPovPersonaContext:
    # Scenario: The persona's voice, signature and forbidden phrases are rendered
    def test_renders_voice_signature_and_forbidden(self) -> None:
        text = pov_persona_context(_pedro())
        assert 'persona "Pedro"' in text
        assert "Direto, técnico, sem rodeios." in text
        assert "Opinião forte, dita na primeira frase." in text
        assert "Quem decide ainda é você." in text
        assert "no mundo de hoje; revolucionário" in text
        assert "nunca O QUE o autor pensa ou viveu" in text

    # Scenario: A persona without phrases says so
    def test_empty_phrase_lists_render_as_none(self) -> None:
        text = pov_persona_context(PersonaProfile(name="Pedro"))
        assert "Frases proibidas (nunca use, nem parafraseadas): nenhuma" in text

    # Scenario: A project without a persona gets an explicit empty context
    def test_no_persona_is_explicitly_empty(self) -> None:
        assert pov_persona_context(None) == NO_PERSONA_CONTEXT == ""


@pytest.mark.unit
class TestOutlinePrompt:
    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        get_ai_response_cache().clear()

    async def _prompt_for(self, persona: PersonaProfile | None) -> str:
        llm = AsyncMock()
        outline = [
            {"slide_index": i, "title": role} for i, role in enumerate(_ROLES, 1)
        ]
        llm.ainvoke.return_value = MagicMock(content=json.dumps(outline))
        await OutlineAgent(llm=llm).generate_pov_outline(_request(persona))
        return str(llm.ainvoke.call_args.args[0])

    # Scenario: The POV outline prompt carries the persona context
    @pytest.mark.asyncio
    async def test_outline_prompt_has_the_persona(self) -> None:
        prompt = await self._prompt_for(_pedro())
        assert 'VOZ DO AUTOR (persona "Pedro")' in prompt
        assert "revolucionário" in prompt

    @pytest.mark.asyncio
    async def test_outline_prompt_without_persona_has_no_voice_block(self) -> None:
        prompt = await self._prompt_for(None)
        assert "VOZ DO AUTOR" not in prompt
