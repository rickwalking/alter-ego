"""Unit tests for ContentDraftAgent."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.content_draft_agent import ContentDraftAgent
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache


class TestContentDraftAgent:
    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        get_ai_response_cache().clear()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> ContentDraftAgent:
        return ContentDraftAgent(llm=mock_llm)

    async def test_draft_slide_returns_parsed_fields(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        payload = {
            "draft_text": "Slide copy",
            "confidence_score": 0.9,
            "sources_used": ["source-1"],
        }
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))

        result = await agent.draft_slide(1, "Title", ["Point"])

        assert result["draft_text"] == "Slide copy"
        assert result["confidence_score"] == 0.9

    async def test_draft_slide_with_persona_enforces_voice(
        self, agent: ContentDraftAgent, mock_llm: AsyncMock
    ) -> None:
        draft_payload = {
            "draft_text": "Raw copy",
            "confidence_score": 0.8,
            "sources_used": [],
        }
        mock_llm.ainvoke.side_effect = [
            MagicMock(content=json.dumps(draft_payload)),
            MagicMock(content="Persona-enforced copy"),
        ]
        persona = PersonaProfile(name="Pedro")

        result = await agent.draft_slide(1, "Title", ["Point"], persona=persona)

        assert result["draft_text"] == "Persona-enforced copy"
        assert mock_llm.ainvoke.call_count == 2
