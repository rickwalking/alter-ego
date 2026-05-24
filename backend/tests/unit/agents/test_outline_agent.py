"""Unit tests for OutlineAgent."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.outline_agent import OutlineAgent


class TestOutlineAgent:
    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> OutlineAgent:
        return OutlineAgent(llm=mock_llm)

    async def test_generate_outline_returns_slides(
        self, agent: OutlineAgent, mock_llm: AsyncMock
    ) -> None:
        outline = [{"slide_index": 1, "title": "Hook", "key_points": ["Open strong"]}]
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(outline))

        result = await agent.generate_outline("Topic", "Devs", "Brief", ["Source"])

        assert len(result) == 1
        assert result[0]["title"] == "Hook"
