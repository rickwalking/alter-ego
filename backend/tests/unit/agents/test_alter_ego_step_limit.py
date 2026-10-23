"""The Alter-Ego answers honestly when it runs out of steps or searches.

Feature file: tests/features/chat_errors.feature
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.errors import GraphRecursionError
from structlog.testing import capture_logs

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.alter_ego_knowledge import AlterEgoKnowledge
from rag_backend.agents.chat_fallback import looks_portuguese, no_knowledge_reply
from rag_backend.application.tools.knowledge_base import (
    SearchToolOptions,
    build_search_documents_tool,
)
from rag_backend.application.tools.knowledge_base.search_documents import (
    QUERY_HASH_CHARS,
)
from rag_backend.domain.constants.chat_stream import (
    ALTER_EGO_RECURSION_LIMIT,
    NO_KNOWLEDGE_REPLY_EN,
    NO_KNOWLEDGE_REPLY_PT,
    SEARCH_BUDGET_EXHAUSTED,
    SEARCH_NO_RESULTS,
)
from rag_backend.infrastructure.config.settings import Settings


class _LoopingGraph:
    """A compiled graph that emits ``tokens`` and then hits the step limit."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.config: dict[str, object] = {}

    async def astream_events(
        self, _payload: object, config: dict[str, object], **_kwargs: object
    ) -> AsyncIterator[dict[str, object]]:
        self.config = config
        for token in self.tokens:
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content=token)},
            }
        raise GraphRecursionError(ALTER_EGO_RECURSION_LIMIT)


def _agent(graph: _LoopingGraph) -> AlterEgoAgent:
    settings = MagicMock(spec=Settings)
    settings.anthropic_api_key = "test"
    settings.anthropic_model = "claude-test"
    settings.llm_provider = "anthropic"
    agent = AlterEgoAgent(
        settings=settings,
        retriever=AsyncMock(),
        message_repository=AsyncMock(),
        document_repository=AsyncMock(),
    )
    agent._agent = graph
    return agent


async def _stream(agent: AlterEgoAgent, message: str) -> list[dict[str, object]]:
    return [
        event
        async for event in agent._chat_stream(
            message, uuid4(), [], persist_messages=False
        )
    ]


@pytest.mark.asyncio
async def test_step_limit_becomes_an_honest_reply() -> None:
    """Running out of steps yields the fallback reply and a server warning.

    Scenario: A question the knowledge base cannot answer gets an honest reply
    """
    graph = _LoopingGraph([])
    with capture_logs() as logs:
        events = await _stream(_agent(graph), "Give me a link to your blog")

    assert events == [
        {"type": "token", "content": NO_KNOWLEDGE_REPLY_EN},
        {"type": "complete", "content": NO_KNOWLEDGE_REPLY_EN},
    ]
    assert graph.config["recursion_limit"] == ALTER_EGO_RECURSION_LIMIT
    assert any(log["event"] == "alter_ego_step_limit_reached" for log in logs)


@pytest.mark.asyncio
async def test_fallback_follows_partial_text_on_a_new_paragraph() -> None:
    """Text streamed before the limit is kept; the fallback starts a new paragraph.

    Scenario: A question the knowledge base cannot answer gets an honest reply
    """
    events = await _stream(_agent(_LoopingGraph(["Hmm, "])), "Oi, tudo bem?")

    assert events[-1] == {
        "type": "complete",
        "content": f"Hmm, \n\n{NO_KNOWLEDGE_REPLY_PT}",
    }


@pytest.mark.parametrize(
    ("message", "portuguese"),
    [
        ("Quem é você?", True),
        ("oi, qual o seu trabalho", True),
        ("Who are you and what can you help me with?", False),
        ("What is 2+2?", False),
        ("Can I see your résumé?", False),
        ("Tell me about your café project", False),
        ("O que é RAG?", True),
    ],
)
def test_reply_language_follows_the_visitor(message: str, portuguese: bool) -> None:
    """Portuguese questions get the Portuguese reply, others the English one.

    Scenario: The honest reply is in the visitor's language
    """
    assert looks_portuguese(message) is portuguese
    expected = NO_KNOWLEDGE_REPLY_PT if portuguese else NO_KNOWLEDGE_REPLY_EN
    assert no_knowledge_reply(message) == expected


@pytest.mark.asyncio
async def test_search_tool_stops_after_its_budget() -> None:
    """The 4th search of a 3-search budget never reaches the knowledge base.

    Scenario: The search tool stops after its budget
    """
    search = MagicMock()
    search.search = AsyncMock(return_value=[])
    tool = build_search_documents_tool(search, SearchToolOptions(max_calls=3))

    answers = [await tool.ainvoke({"query": f"q{i}"}) for i in range(4)]

    assert answers == [SEARCH_NO_RESULTS] * 3 + [SEARCH_BUDGET_EXHAUSTED]
    assert search.search.await_count == 3


@pytest.mark.asyncio
async def test_search_tool_without_budget_keeps_searching() -> None:
    """The default tool (the carousel chat's) has no budget.

    Scenario: The search tool stops after its budget
    """
    search = MagicMock()
    search.search = AsyncMock(return_value=[])
    tool = build_search_documents_tool(search)

    for i in range(5):
        await tool.ainvoke({"query": f"q{i}"})

    assert search.search.await_count == 5


class _ScriptedToolModel(BaseChatModel):
    """A chat model that replays scripted replies (tool calls, then an answer)."""

    replies: list[AIMessage]

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, *_args: object, **_kwargs: object) -> "_ScriptedToolModel":
        return self

    def _generate(
        self, messages: list[BaseMessage], *_args: object, **_kwargs: object
    ) -> ChatResult:
        del messages
        return ChatResult(generations=[ChatGeneration(message=self.replies.pop(0))])


def _search_call(index: int) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "_search_documents",
                "args": {"query": f"q{index}"},
                "id": f"c{index}",
            }
        ],
    )


@pytest.mark.asyncio
async def test_real_harness_fits_the_search_budget_within_the_step_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On the real deep-agent graph, 4 searches (one refused) and an answer fit the limit.

    Scenario: The search tool stops after its budget
    """
    from rag_backend.agents import alter_ego_agent as agent_module

    model = _ScriptedToolModel(
        replies=[_search_call(i) for i in range(4)] + [AIMessage(content="answer")]
    )
    monkeypatch.setattr(agent_module, "build_chat_model", lambda _settings: model)
    search = MagicMock()
    search.search = AsyncMock(return_value=[])
    agent = AlterEgoAgent(
        settings=MagicMock(spec=Settings),
        retriever=AsyncMock(),
        message_repository=AsyncMock(),
        document_repository=AsyncMock(),
        knowledge=AlterEgoKnowledge(search=search),
    )

    with capture_logs() as logs:
        events = await _stream(agent, "Who are you?")

    assert search.search.await_count == 3
    assert not any(log["event"] == "alter_ego_step_limit_reached" for log in logs)
    assert NO_KNOWLEDGE_REPLY_EN not in str(events)
    assert model.replies == []


@pytest.mark.asyncio
async def test_search_logs_never_carry_the_visitor_text() -> None:
    """Search logs carry the query's length and hash, never its words.

    Scenario: Search logs never contain the visitor's words
    """
    search = MagicMock()
    search.search = AsyncMock(return_value=[])
    tool = build_search_documents_tool(search, SearchToolOptions(max_calls=1))
    secret = "my private medical question"

    with capture_logs() as logs:
        await tool.ainvoke({"query": secret})
        await tool.ainvoke({"query": secret})

    search_logs = [log for log in logs if str(log["event"]).startswith("search_")]
    assert {log["event"] for log in search_logs} == {
        "search_documents_called",
        "search_documents_no_results",
        "search_documents_budget_exhausted",
    }
    for log in search_logs:
        assert secret not in str(log)
        assert log["query_length"] == len(secret)
        assert len(str(log["query_hash"])) == QUERY_HASH_CHARS
