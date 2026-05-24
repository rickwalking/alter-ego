"""Unit tests for SourceSynthesisAgent."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent


class TestSourceSynthesisAgent:
    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> SourceSynthesisAgent:
        return SourceSynthesisAgent(llm=mock_llm)

    async def test_extract_key_points_parses_json(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        payload = {"key_points": ["Point A", "Point B"], "summary": "Summary text"}
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))

        result = await agent.extract_key_points("Title", "Content body", "document")

        assert result["key_points"] == ["Point A", "Point B"]
        assert result["summary"] == "Summary text"

    async def test_extract_key_points_invalid_json_raises(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        mock_llm.ainvoke.return_value = MagicMock(content="not-json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            await agent.extract_key_points("Title", "Content", "document")
