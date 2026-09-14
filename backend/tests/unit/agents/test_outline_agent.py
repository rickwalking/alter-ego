"""Unit tests for OutlineAgent."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache


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


class TestOutlineCachePoisoning:
    """AE-0330: an unparseable response must never be cached.

    Live 2026-09-14: GLM 5.2 spent 31999 of its 32000 tokens reasoning and
    returned empty content. That empty string was cached, so every retry failed
    in milliseconds without calling the model for the whole TTL window.
    """

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        get_ai_response_cache().clear()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> OutlineAgent:
        return OutlineAgent(llm=mock_llm)

    @staticmethod
    def _outline() -> list[dict[str, object]]:
        return [{"slide_index": 1, "title": "Hook", "key_points": ["Open strong"]}]

    async def test_empty_response_is_not_cached_so_retry_reaches_the_model(
        self, agent: OutlineAgent, mock_llm: AsyncMock
    ) -> None:
        # Scenario: an empty model response does not poison the retry (AE-0330)
        mock_llm.ainvoke.side_effect = [
            MagicMock(content=""),
            MagicMock(content=json.dumps(self._outline())),
        ]
        with pytest.raises(ValueError, match="Invalid JSON"):
            await agent.generate_outline("Topic", "Devs", "Brief", ["Source"])

        result = await agent.generate_outline("Topic", "Devs", "Brief", ["Source"])

        assert result[0]["title"] == "Hook"
        assert mock_llm.ainvoke.await_count == 2  # retry hit the LLM, not a cache

    async def test_poisoned_cache_entry_is_evicted(
        self, agent: OutlineAgent, mock_llm: AsyncMock
    ) -> None:
        # Scenario: a poisoned entry from an older deploy is evicted (AE-0330)
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(self._outline()))
        await agent.generate_outline("Topic", "Devs", "Brief", ["Source"])
        prompt = mock_llm.ainvoke.call_args[0][0][0].content
        get_ai_response_cache().set(prompt, agent.model_id, "poisoned-not-json")

        result = await agent.generate_outline("Topic", "Devs", "Brief", ["Source"])

        assert result[0]["title"] == "Hook"
        assert mock_llm.ainvoke.await_count == 2  # evicted, so the model ran again
