"""Tests for the researcher subagent + research @tool adapters.

Covers tests/features/researcher_subagent_url_navigation.feature:
- the scrape_url / search_web @tool adapters delegate via the ResearchTool Protocol
- a scrape failure degrades gracefully (reported, not raised)
- the researcher subagent spec uses the DeepAgents tools/prompt/model fields and
  grants scrape_url + search_web + search_documents
- deterministic carousel phases stay LangGraph nodes, not task-delegated subagents
"""

from __future__ import annotations

from typing import cast

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool, tool

from rag_backend.agents.carousel_workflow_graph import build_carousel_workflow_graph
from rag_backend.agents.subagents import (
    RESEARCHER_SUBAGENT_NAME,
    ResearcherSubagentConfig,
    build_researcher_subagent,
)
from rag_backend.agents.subagents.constants import (
    SPEC_FIELD_DESCRIPTION,
    SPEC_FIELD_MODEL,
    SPEC_FIELD_NAME,
    SPEC_FIELD_PROMPT,
    SPEC_FIELD_TOOLS,
)
from rag_backend.agents.tools import build_scrape_url_tool, build_search_web_tool
from rag_backend.agents.tools.constants import (
    SCRAPE_BLOCKED_PREFIX,
    SCRAPE_FAILURE_PREFIX,
)
from rag_backend.application.services.carousel.phase_subagents import (
    build_phase_subagent_specs,
)
from rag_backend.domain.models import ResearchSourceType


class _StubResearch:
    """ResearchTool Protocol stub — no Playwright, no network (CI-safe)."""

    def __init__(
        self,
        *,
        page: str = "",
        results: list[dict[str, str]] | None = None,
        scrape_error: Exception | None = None,
    ) -> None:
        self._page = page
        self._results = results or []
        self._scrape_error = scrape_error
        self.scrape_calls: list[str] = []
        self.search_calls: list[tuple[str, list[ResearchSourceType]]] = []

    async def scrape_url(self, url: str) -> str:
        self.scrape_calls.append(url)
        if self._scrape_error is not None:
            raise self._scrape_error
        return self._page

    async def search_web(
        self, query: str, _source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]:
        self.search_calls.append((query, _source_types))
        return self._results


@tool
async def _fake_search_documents(query: str) -> str:
    """Stub knowledge-base search tool.

    Args:
        query: search string
    """
    return f"docs:{query}"


def _config(
    research: _StubResearch, *, model: BaseChatModel | None = None
) -> ResearcherSubagentConfig:
    return ResearcherSubagentConfig(
        research=research,
        search_documents=_fake_search_documents,
        model=model,
    )


async def test_scrape_url_adapter_delegates() -> None:
    """Scenario: The scrape_url adapter delegates to the service via the Protocol"""
    research = _StubResearch(page="PAGE BODY")
    adapter = build_scrape_url_tool(research)
    result = await adapter.ainvoke({"url": "https://example.com"})
    assert result == "PAGE BODY"
    assert research.scrape_calls == ["https://example.com"]


async def test_scrape_url_adapter_degrades_on_failure() -> None:
    """Scenario: A scrape failure degrades gracefully"""
    research = _StubResearch(scrape_error=ConnectionError("boom"))
    adapter = build_scrape_url_tool(research)
    result = await adapter.ainvoke({"url": "https://down.example"})
    assert result.startswith(SCRAPE_FAILURE_PREFIX)
    assert "https://down.example" in result
    assert "boom" in result


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost/admin",
        "http://127.0.0.1:8000/",
        "http://10.0.0.5/internal",
        "http://[::1]/",
    ],
)
async def test_scrape_url_adapter_blocks_unsafe_targets(unsafe_url: str) -> None:
    """The guard must short-circuit before the service is ever invoked.

    Scenario: The scrape_url adapter blocks SSRF targets before delegating (QA F-1)
    """
    research = _StubResearch(page="SECRET")
    adapter = build_scrape_url_tool(research)
    result = await adapter.ainvoke({"url": unsafe_url})
    assert result.startswith(SCRAPE_BLOCKED_PREFIX)
    assert research.scrape_calls == []


async def test_scrape_url_adapter_allows_public_url() -> None:
    """Scenario: A safe public http(s) URL is still delegated after the guard"""
    research = _StubResearch(page="PAGE BODY")
    adapter = build_scrape_url_tool(research)
    result = await adapter.ainvoke({"url": "https://example.com/article"})
    assert result == "PAGE BODY"
    assert research.scrape_calls == ["https://example.com/article"]


async def test_search_web_adapter_formats_sources() -> None:
    """Scenario: The search_web adapter delegates to the service via the Protocol"""
    research = _StubResearch(
        results=[
            {"title": "T1", "url": "https://a", "snippet": "S1"},
            {"title": "T2", "url": "https://b", "snippet": "S2"},
        ]
    )
    adapter = build_search_web_tool(research)
    result = await adapter.ainvoke({"query": "rust"})
    assert research.search_calls[0][0] == "rust"
    assert "[1] T1 (https://a)" in result
    assert "[2] T2 (https://b)" in result


async def test_search_web_adapter_empty() -> None:
    research = _StubResearch(results=[])
    adapter = build_search_web_tool(research)
    result = await adapter.ainvoke({"query": "none"})
    assert "No web results found." in result


def test_researcher_spec_uses_deepagents_fields() -> None:
    """There is no bespoke skills key, only DeepAgents-standard fields.

    Scenario: Subagent specs use the DeepAgents tools/prompt/model fields
    """
    research = _StubResearch()
    stub_model = cast("BaseChatModel", object())
    spec = build_researcher_subagent(_config(research, model=stub_model))

    assert spec[SPEC_FIELD_NAME] == RESEARCHER_SUBAGENT_NAME
    assert isinstance(spec[SPEC_FIELD_DESCRIPTION], str)
    assert isinstance(spec[SPEC_FIELD_PROMPT], str) and spec[SPEC_FIELD_PROMPT]
    assert spec[SPEC_FIELD_MODEL] is stub_model
    assert "skills" not in spec


def test_researcher_spec_grants_three_tools() -> None:
    """The model field is omitted when none is supplied."""
    research = _StubResearch()
    spec = build_researcher_subagent(_config(research))
    tools = spec[SPEC_FIELD_TOOLS]
    assert isinstance(tools, list)
    names = {cast("BaseTool", t).name for t in tools}
    assert names == {"scrape_url", "search_web", "_fake_search_documents"}
    assert SPEC_FIELD_MODEL not in spec


def test_deterministic_phases_are_langgraph_nodes_not_subagents() -> None:
    """Phase subagent specs carry no runnable, task or tools: they are deterministic
    nodes, not tool-wielding delegated subagents.

    Scenario: Deterministic phases stay LangGraph nodes
    """
    compiled = build_carousel_workflow_graph().compile()
    node_names = set(compiled.get_graph().nodes)
    for phase in ("outline", "content", "design", "images", "final_review"):
        assert phase in node_names

    for phase_spec in build_phase_subagent_specs():
        assert "runnable" not in phase_spec
        assert "task" not in phase_spec
        assert phase_spec[SPEC_FIELD_TOOLS] == []


def test_rag_agent_registers_researcher_subagent() -> None:
    """Scenario: Researcher subagent is registered in the chat pipeline"""
    from unittest.mock import MagicMock

    from rag_backend.agents.chat_knowledge import PUBLIC_KNOWLEDGE
    from rag_backend.agents.rag_agent import RAGAgent
    from rag_backend.agents.subagents import RESEARCHER_SUBAGENT_NAME

    agent = RAGAgent.__new__(RAGAgent)
    agent._editorial_subagent = {"name": "editorial-carousel"}
    agent._research_tool = MagicMock()
    agent._carousel_tool_access = MagicMock()
    agent._knowledge_search = MagicMock()
    agent._scope = PUBLIC_KNOWLEDGE
    agent._llm = MagicMock()

    specs = agent._build_subagents()

    names = [spec["name"] for spec in specs]
    assert names[0] == "editorial-carousel"
    assert RESEARCHER_SUBAGENT_NAME in names


def test_rag_agent_skips_researcher_without_tool_access() -> None:
    """Scenario: Researcher subagent is registered in the chat pipeline (negative half)"""
    from unittest.mock import MagicMock

    from rag_backend.agents.chat_knowledge import PUBLIC_KNOWLEDGE
    from rag_backend.agents.rag_agent import RAGAgent
    from rag_backend.agents.subagents import RESEARCHER_SUBAGENT_NAME

    agent = RAGAgent.__new__(RAGAgent)
    agent._editorial_subagent = None
    agent._research_tool = MagicMock()
    agent._carousel_tool_access = None
    agent._knowledge_search = MagicMock()
    agent._scope = PUBLIC_KNOWLEDGE
    agent._llm = MagicMock()

    specs = agent._build_subagents()

    assert RESEARCHER_SUBAGENT_NAME not in [spec["name"] for spec in specs]


def test_rag_agent_skips_researcher_without_research_tool() -> None:
    """Scenario: Researcher subagent is registered in the chat pipeline"""
    from unittest.mock import MagicMock

    from rag_backend.agents.chat_knowledge import PUBLIC_KNOWLEDGE
    from rag_backend.agents.rag_agent import RAGAgent
    from rag_backend.agents.subagents import RESEARCHER_SUBAGENT_NAME

    agent = RAGAgent.__new__(RAGAgent)
    agent._editorial_subagent = {"name": "editorial-carousel"}
    agent._research_tool = None
    agent._carousel_tool_access = MagicMock()
    agent._knowledge_search = MagicMock()
    agent._scope = PUBLIC_KNOWLEDGE
    agent._llm = MagicMock()

    specs = agent._build_subagents()

    assert RESEARCHER_SUBAGENT_NAME not in [spec["name"] for spec in specs]
