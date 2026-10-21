"""Assertion-bearing tests that pin exact SourceSynthesisAgent behaviour.

Feature: Source synthesis hardening
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from structlog.testing import capture_logs

from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.domain.constants.ai_agents import (
    ERR_INVALID_JSON,
    PROMPT_SOURCE_SYNTHESIS,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import JSON_REPAIR_PROMPT

CONFIG_PATH = "rag_backend.agents.source_synthesis_agent.get_langfuse_runnable_config"
RUNNABLE_CONFIG = {"callbacks": ["langfuse-marker"]}
MODEL_ID = "synthesis-model-marker"
VALID_PAYLOAD = json.dumps({"key_points": ["A"], "summary": "S"})


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Start every test with an empty response cache."""
    get_ai_response_cache().clear()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """An LLM returning a valid payload."""
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(content=VALID_PAYLOAD)
    return llm


@pytest.fixture
def agent(mock_llm: AsyncMock) -> SourceSynthesisAgent:
    """An agent with a distinctive model id."""
    return SourceSynthesisAgent(llm=mock_llm, model_id=MODEL_ID)


def _prompt(source_type: str) -> str:
    """The synthesis prompt for the default title and content."""
    return PROMPT_SOURCE_SYNTHESIS.format(
        title="T", source_type=source_type, content="C"
    )


# Scenario: The source type defaults to document
async def test_default_source_type_is_document(
    agent: SourceSynthesisAgent, mock_llm: AsyncMock
) -> None:
    """Omitting the source type sends the document type in the prompt."""
    with patch(CONFIG_PATH, return_value=RUNNABLE_CONFIG):
        await agent.extract_key_points("T", "C")

    mock_llm.ainvoke.assert_awaited_once_with(
        [HumanMessage(content=_prompt("document"))], RUNNABLE_CONFIG
    )


# Scenario: A malformed answer is repaired with the exact repair conversation
async def test_repair_call_sends_raw_and_repair_prompt(
    agent: SourceSynthesisAgent, mock_llm: AsyncMock
) -> None:
    """The repair round-trip replays the raw answer and the repair prompt."""
    mock_llm.ainvoke.side_effect = [
        MagicMock(content="not-json"),
        MagicMock(content=VALID_PAYLOAD),
    ]

    with patch(CONFIG_PATH, return_value=RUNNABLE_CONFIG):
        result = await agent.extract_key_points("T", "C", "web")

    assert result == {"key_points": ["A"], "summary": "S"}
    assert mock_llm.ainvoke.await_args_list[1].args == (
        [AIMessage(content="not-json"), HumanMessage(content=JSON_REPAIR_PROMPT)],
        RUNNABLE_CONFIG,
    )


# Scenario: A poisoned cache entry is evicted by its exact key
async def test_poisoned_cache_entry_is_deleted_by_prompt_and_model(
    agent: SourceSynthesisAgent,
) -> None:
    """Eviction deletes the entry for the prompt and the agent model id."""
    cache = MagicMock()
    cache.get = MagicMock(return_value="poisoned")
    agent._cache = cache

    await agent.extract_key_points("T", "C", "web")

    cache.delete.assert_called_once_with(_prompt("web"), MODEL_ID)


# Scenario: The second parse failure is logged with model id and truncated payload
async def test_second_parse_failure_log_fields(
    agent: SourceSynthesisAgent, mock_llm: AsyncMock
) -> None:
    """The attempt-2 log carries the model id and the first 500 chars."""
    mock_llm.ainvoke.side_effect = [
        MagicMock(content="bad"),
        MagicMock(content="y" * 600),
    ]

    with capture_logs() as logs, pytest.raises(ValueError):
        await agent.extract_key_points("T", "C", "web")

    second = [
        log
        for log in logs
        if log["event"] == "source_synthesis_json_parse_failed_attempt_2"
    ]
    assert len(second) == 1
    assert second[0]["model_id"] == MODEL_ID
    assert second[0]["repair_response"] == "y" * 500


# Scenario: A failing repair call is logged with the model id
async def test_repair_call_failure_log_has_model_id(
    agent: SourceSynthesisAgent, mock_llm: AsyncMock
) -> None:
    """The repair transport failure log carries the model id."""
    mock_llm.ainvoke.side_effect = [MagicMock(content="bad"), RuntimeError("boom")]

    with capture_logs() as logs, pytest.raises(ValueError):
        await agent.extract_key_points("T", "C", "web")

    failures = [
        log for log in logs if log["event"] == "source_synthesis_repair_call_failed"
    ]
    assert len(failures) == 1
    assert failures[0]["model_id"] == MODEL_ID


# Scenario: A non-object JSON answer is rejected with the invalid JSON error
def test_parse_response_rejects_non_object(agent: SourceSynthesisAgent) -> None:
    """A JSON list raises TypeError carrying the invalid JSON message."""
    with pytest.raises(TypeError, match=ERR_INVALID_JSON):
        agent._parse_response("[1, 2]")


# Scenario: Non-list key points become an empty list
def test_parse_response_non_list_key_points_become_empty(
    agent: SourceSynthesisAgent,
) -> None:
    """A string key_points value is replaced by an empty list."""
    result = agent._parse_response(json.dumps({"key_points": "x", "summary": "S"}))

    assert result == {"key_points": [], "summary": "S"}


# Scenario: A missing summary becomes an empty string
def test_parse_response_missing_summary_is_empty(agent: SourceSynthesisAgent) -> None:
    """No summary key yields an empty summary string."""
    result = agent._parse_response(json.dumps({"key_points": ["A"]}))

    assert result == {"key_points": ["A"], "summary": ""}
