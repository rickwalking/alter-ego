"""The carousel (RAG) chat reads personal knowledge only for the site owner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.tools import BaseTool

from rag_backend.agents.chat_knowledge import (
    OWNER_KNOWLEDGE,
    PUBLIC_KNOWLEDGE,
    ChatKnowledge,
    KnowledgeScope,
)
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.api.dependencies.agents import RagAgentBuildContext, build_rag_agent
from rag_backend.domain.constants.namespaces import NAMESPACE_PERSONAL, NAMESPACE_PUBLIC
from rag_backend.domain.models import Document, DocumentScope, DocumentStatus
from rag_backend.infrastructure.config.settings import Settings

_SITE_OWNER = str(uuid4())


def _settings() -> MagicMock:
    settings = MagicMock(spec=Settings)
    settings.anthropic_api_key = "test"
    settings.anthropic_model = "claude-test"
    settings.llm_provider = "anthropic"
    return settings


def _document(title: str, scope: DocumentScope) -> Document:
    return Document(
        content=title,
        title=title,
        scope=scope,
        status=DocumentStatus.COMPLETED,
        chunk_count=1,
    )


def _agent(knowledge: ChatKnowledge | None) -> tuple[RAGAgent, MagicMock]:
    search = MagicMock()
    search.search = AsyncMock(return_value=[])
    repository = AsyncMock()
    repository.get_all = AsyncMock(
        return_value=[
            _document("Private notes", DocumentScope.PERSONAL),
            _document("Public bio", DocumentScope.PUBLIC),
        ]
    )
    if knowledge is not None:
        knowledge = ChatKnowledge(search=search, scope=knowledge.scope)
    agent = RAGAgent(
        settings=_settings(),
        retriever=AsyncMock(),
        message_repository=AsyncMock(),
        document_repository=repository,
        knowledge=knowledge,
    )
    return agent, search


def _tool(agent: RAGAgent, name: str) -> BaseTool:
    return next(t for t in agent._build_tools() if t.name.lstrip("_") == name)


@pytest.mark.parametrize(
    ("scope", "prefix", "listed"),
    [
        (PUBLIC_KNOWLEDGE, NAMESPACE_PUBLIC, {"Public bio"}),
        (OWNER_KNOWLEDGE, NAMESPACE_PERSONAL, {"Public bio", "Private notes"}),
    ],
)
async def test_rag_agent_tools_follow_the_scope(
    scope: KnowledgeScope, prefix: str, listed: set[str]
) -> None:
    """Scenario: The carousel chat reads personal knowledge only for the site owner"""
    agent, search = _agent(ChatKnowledge(scope=scope))

    await _tool(agent, "search_documents").ainvoke({"query": "career"})
    listing = await _tool(agent, "list_documents").ainvoke({})

    assert search.search.await_args.args[0].namespace_prefix == prefix
    assert {title for title in ("Public bio", "Private notes") if title in listing} == (
        listed
    )


async def test_rag_agent_without_a_scope_reads_public_only() -> None:
    """Scenario: A chat agent built without a knowledge scope reads public knowledge only"""
    agent, _ = _agent(None)

    await agent.search_documents("career")

    query = agent._retriever.retrieve.await_args.args[0]
    assert query.namespace_prefix == NAMESPACE_PUBLIC


@pytest.mark.parametrize(
    ("owner_user_id", "expected"),
    [
        (_SITE_OWNER, OWNER_KNOWLEDGE),
        (str(uuid4()), PUBLIC_KNOWLEDGE),
        (None, PUBLIC_KNOWLEDGE),
    ],
    ids=["site-owner", "editor", "no-owner"],
)
def test_build_rag_agent_picks_the_scope_from_the_owner(
    owner_user_id: str | None, expected: KnowledgeScope
) -> None:
    """Scenario: The carousel chat reads personal knowledge only for the site owner"""
    container = MagicMock()
    container.settings.return_value = Settings(autopilot_owner_user_id=_SITE_OWNER)

    with patch("rag_backend.api.dependencies.agents.RAGAgent") as rag_agent:
        build_rag_agent(
            AsyncMock(), container, RagAgentBuildContext(owner_user_id=owner_user_id)
        )

    assert rag_agent.call_args.kwargs["knowledge"].scope is expected
