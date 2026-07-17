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

    async def test_extract_key_points_parses_markdown_fenced_json(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        payload = {"key_points": ["Point A"], "summary": "Summary text"}
        mock_llm.ainvoke.return_value = MagicMock(
            content=f"```json\n{json.dumps(payload)}\n```"
        )

        result = await agent.extract_key_points(
            "Markdown Title", "Markdown content body", "document"
        )

        assert result["key_points"] == ["Point A"]
        assert result["summary"] == "Summary text"

    async def test_extract_key_points_invalid_json_raises(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        mock_llm.ainvoke.return_value = MagicMock(content="not-json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            await agent.extract_key_points("Title", "Content", "document")


class TestSourceSynthesisHardening:
    """AE-0318 scenarios (tests/features/source_synthesis_hardening.feature)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        from rag_backend.infrastructure.cache.ai_response_cache import (
            get_ai_response_cache,
        )

        get_ai_response_cache().clear()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> SourceSynthesisAgent:
        return SourceSynthesisAgent(llm=mock_llm)

    async def test_truncated_response_triggers_one_repair_retry(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        """Scenario: Truncated response triggers one repair retry."""
        payload = {"key_points": ["Repaired point"], "summary": "Repaired"}
        mock_llm.ainvoke.side_effect = [
            MagicMock(content='```json\n{\n  "key_points": [\n    "The provided'),
            MagicMock(content=json.dumps(payload)),
        ]

        result = await agent.extract_key_points("title", "content body", "document")

        assert result["key_points"] == ["Repaired point"]
        assert mock_llm.ainvoke.await_count == 2

    async def test_repaired_response_is_cached_not_the_malformed_raw(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        """Scenario: Truncated response triggers one repair retry (cache half)."""
        payload = {"key_points": ["Repaired point"], "summary": "Repaired"}
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="not-json"),
            MagicMock(content=json.dumps(payload)),
        ]
        await agent.extract_key_points("title", "content body", "document")

        result = await agent.extract_key_points("title", "content body", "document")

        assert result["key_points"] == ["Repaired point"]
        assert mock_llm.ainvoke.await_count == 2  # second call served from cache

    async def test_repair_failure_raises_and_does_not_poison_cache(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        """Scenario: Retry after a transient malformed response is not poisoned."""
        payload = {"key_points": ["Fresh point"], "summary": "Fresh"}
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="not-json"),
            MagicMock(content="still-not-json"),
            MagicMock(content=json.dumps(payload)),
        ]
        with pytest.raises(ValueError, match="Invalid JSON"):
            await agent.extract_key_points("title", "content body", "document")

        result = await agent.extract_key_points("title", "content body", "document")

        assert result["key_points"] == ["Fresh point"]
        assert mock_llm.ainvoke.await_count == 3  # retry hit the LLM, not a cache

    async def test_poisoned_cache_entry_is_evicted(
        self, agent: SourceSynthesisAgent, mock_llm: AsyncMock
    ) -> None:
        """Scenario: Poisoned cache entry from a previous deploy is evicted."""
        from rag_backend.domain.constants.ai_agents import PROMPT_SOURCE_SYNTHESIS
        from rag_backend.infrastructure.cache.ai_response_cache import (
            get_ai_response_cache,
        )

        prompt = PROMPT_SOURCE_SYNTHESIS.format(
            title="title", source_type="document", content="content body"
        )
        get_ai_response_cache().set(prompt, agent.model_id, "poisoned-not-json")
        payload = {"key_points": ["Fresh point"], "summary": "Fresh"}
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))

        result = await agent.extract_key_points("title", "content body", "document")

        assert result["key_points"] == ["Fresh point"]
        assert mock_llm.ainvoke.await_count == 1
        assert get_ai_response_cache().get(prompt, agent.model_id) == json.dumps(
            payload
        )


class TestSourceSynthesisRepairTransport:
    """AE-0318 review r1 (M2): repair transport failure keeps the 400 contract."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        from rag_backend.infrastructure.cache.ai_response_cache import (
            get_ai_response_cache,
        )

        get_ai_response_cache().clear()

    async def test_repair_transport_failure_raises_value_error(self) -> None:
        """Scenario: Repair failure fails closed with an observable error."""
        mock_llm = AsyncMock()
        agent = SourceSynthesisAgent(llm=mock_llm)
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="not-json"),
            RuntimeError("provider stream aborted"),
        ]

        with pytest.raises(ValueError, match="Invalid JSON"):
            await agent.extract_key_points("title", "content body", "document")

    async def test_valid_response_is_reused_from_cache(self) -> None:
        """Scenario: Valid response is parsed and cached (reuse half)."""
        mock_llm = AsyncMock()
        agent = SourceSynthesisAgent(llm=mock_llm)
        payload = {"key_points": ["Point A"], "summary": "S"}
        mock_llm.ainvoke.return_value = MagicMock(content=json.dumps(payload))

        first = await agent.extract_key_points("title", "content body", "document")
        second = await agent.extract_key_points("title", "content body", "document")

        assert first == second
        assert mock_llm.ainvoke.await_count == 1


class TestSourceSynthesisObservability:
    """AE-0318: the hardening's structlog events fire with the right fields."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        from rag_backend.infrastructure.cache.ai_response_cache import (
            get_ai_response_cache,
        )

        get_ai_response_cache().clear()

    async def test_parse_failure_logs_both_attempts_with_truncated_payloads(
        self,
    ) -> None:
        """Scenario: Repair failure fails closed (observability half)."""
        from structlog.testing import capture_logs

        mock_llm = AsyncMock()
        agent = SourceSynthesisAgent(llm=mock_llm)
        long_garbage = "x" * 600
        mock_llm.ainvoke.side_effect = [
            MagicMock(content=long_garbage),
            MagicMock(content="still-not-json"),
        ]

        with capture_logs() as logs, pytest.raises(ValueError):
            await agent.extract_key_points("title", "content body", "document")

        first = [
            log
            for log in logs
            if log["event"] == "source_synthesis_json_parse_failed_attempt_1"
        ]
        second = [
            log
            for log in logs
            if log["event"] == "source_synthesis_json_parse_failed_attempt_2"
        ]
        assert len(first) == 1 and len(second) == 1
        assert first[0]["model_id"] == agent.model_id
        # The logged payload is truncated to exactly 500 chars.
        assert first[0]["raw_response"] == "x" * 500
        assert second[0]["repair_response"] == "still-not-json"

    async def test_poisoned_cache_eviction_is_logged(self) -> None:
        """Scenario: Poisoned cache entry from a previous deploy is evicted."""
        from structlog.testing import capture_logs

        from rag_backend.domain.constants.ai_agents import PROMPT_SOURCE_SYNTHESIS
        from rag_backend.infrastructure.cache.ai_response_cache import (
            get_ai_response_cache,
        )

        mock_llm = AsyncMock()
        agent = SourceSynthesisAgent(llm=mock_llm)
        prompt = PROMPT_SOURCE_SYNTHESIS.format(
            title="title", source_type="document", content="content body"
        )
        get_ai_response_cache().set(prompt, agent.model_id, "poisoned")
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps({"key_points": [], "summary": ""})
        )

        with capture_logs() as logs:
            await agent.extract_key_points("title", "content body", "document")

        evictions = [
            log
            for log in logs
            if log["event"] == "source_synthesis_poisoned_cache_evicted"
        ]
        assert len(evictions) == 1
        assert evictions[0]["model_id"] == agent.model_id
        assert evictions[0]["log_level"] == "warning"

    async def test_repair_transport_failure_is_logged(self) -> None:
        """Scenario: Repair failure fails closed (transport half)."""
        from structlog.testing import capture_logs

        mock_llm = AsyncMock()
        agent = SourceSynthesisAgent(llm=mock_llm)
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="not-json"),
            RuntimeError("stream aborted"),
        ]

        with capture_logs() as logs, pytest.raises(ValueError):
            await agent.extract_key_points("title", "content body", "document")

        failures = [
            log for log in logs if log["event"] == "source_synthesis_repair_call_failed"
        ]
        assert len(failures) == 1
        assert failures[0]["error"] == "stream aborted"
