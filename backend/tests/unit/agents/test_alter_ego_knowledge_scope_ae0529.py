"""The Alter-Ego chat reads public knowledge only for an anonymous visitor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from langchain_core.tools import BaseTool

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.chat_knowledge import (
    OWNER_KNOWLEDGE,
    PUBLIC_KNOWLEDGE,
    ChatKnowledge,
    KnowledgeScope,
    knowledge_scope_for,
)
from rag_backend.api.dependencies.agents import build_agent_for_conversation
from rag_backend.domain.constants.namespaces import (
    NAMESPACE_PERSONAL,
    NAMESPACE_PUBLIC,
)
from rag_backend.domain.models import (
    Conversation,
    Document,
    DocumentScope,
    DocumentStatus,
    RetrievalQuery,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.retrieval.hybrid_retriever import (
    HybridRetrieverWithRRF,
)

_BUILDER = "rag_backend.api.dependencies.agents.build_alter_ego_agent"


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
        is_public=scope is DocumentScope.PUBLIC,
        status=DocumentStatus.COMPLETED,
        chunk_count=1,
    )


def _repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_all = AsyncMock(
        return_value=[
            _document("Private notes", DocumentScope.PERSONAL),
            _document("Public bio", DocumentScope.PUBLIC),
            _document("Carousel source", DocumentScope.CAROUSEL),
        ]
    )
    return repository


def _agent(scope: KnowledgeScope | None) -> tuple[AlterEgoAgent, MagicMock]:
    search = MagicMock()
    search.search = AsyncMock(return_value=[])
    knowledge = None if scope is None else ChatKnowledge(search=search, scope=scope)
    agent = AlterEgoAgent(
        settings=_settings(),
        retriever=AsyncMock(),
        message_repository=AsyncMock(),
        document_repository=_repository(),
        knowledge=knowledge,
    )
    return agent, search


def _tool(agent: AlterEgoAgent, name: str) -> BaseTool:
    return next(t for t in agent._build_tools() if t.name.lstrip("_") == name)


async def _searched_prefix(agent: AlterEgoAgent, search: MagicMock) -> str | None:
    await _tool(agent, "search_documents").ainvoke({"query": "Who are you?"})
    return search.search.await_args.args[0].namespace_prefix


_SITE_OWNER = uuid4()


@pytest.mark.parametrize(
    ("owner_id", "site_owner", "expected"),
    [
        (_SITE_OWNER, str(_SITE_OWNER), OWNER_KNOWLEDGE),
        (str(_SITE_OWNER).upper(), f" {_SITE_OWNER} ", OWNER_KNOWLEDGE),
        (uuid4(), str(_SITE_OWNER), PUBLIC_KNOWLEDGE),
        (None, str(_SITE_OWNER), PUBLIC_KNOWLEDGE),
        (_SITE_OWNER, "", PUBLIC_KNOWLEDGE),
        (_SITE_OWNER, "not-a-uuid", PUBLIC_KNOWLEDGE),
        ("not-a-uuid", str(_SITE_OWNER), PUBLIC_KNOWLEDGE),
    ],
    ids=[
        "site-owner",
        "site-owner-spelled-differently",
        "editor-or-other-admin",
        "anonymous",
        "setting-unset",
        "setting-invalid",
        "owner-id-invalid",
    ],
)
def test_only_the_site_owner_gets_the_owner_scope(
    owner_id: UUID | str | None, site_owner: str, expected: KnowledgeScope
) -> None:
    """Scenario: An editor's or another admin's chat reads public knowledge only

    Scenario: Without a configured site owner every chat reads public knowledge only
    """
    assert knowledge_scope_for(owner_id, site_owner) is expected


def test_a_setting_that_is_not_text_fails_closed() -> None:
    """Scenario: Without a configured site owner every chat reads public knowledge only"""
    assert knowledge_scope_for(_SITE_OWNER, MagicMock()) is PUBLIC_KNOWLEDGE


def test_scopes_name_the_namespaces_they_read() -> None:
    """Scenario: An anonymous visitor's chat searches public knowledge only"""
    assert PUBLIC_KNOWLEDGE.namespace_prefix == NAMESPACE_PUBLIC
    assert PUBLIC_KNOWLEDGE.document_scopes == frozenset({NAMESPACE_PUBLIC})
    assert OWNER_KNOWLEDGE.namespace_prefix == NAMESPACE_PERSONAL
    assert OWNER_KNOWLEDGE.document_scopes == frozenset({
        NAMESPACE_PERSONAL,
        NAMESPACE_PUBLIC,
    })


def test_retriever_reads_only_the_public_namespace_for_the_public_scope() -> None:
    """Scenario: An anonymous visitor's chat searches public knowledge only"""
    resolve = HybridRetrieverWithRRF._resolve_namespaces
    assert resolve(PUBLIC_KNOWLEDGE.namespace_prefix) == [NAMESPACE_PUBLIC]
    assert resolve(OWNER_KNOWLEDGE.namespace_prefix) == [
        NAMESPACE_PERSONAL,
        NAMESPACE_PUBLIC,
    ]


async def test_public_agent_searches_the_public_namespace() -> None:
    """Scenario: An anonymous visitor's chat searches public knowledge only"""
    agent, search = _agent(PUBLIC_KNOWLEDGE)

    assert await _searched_prefix(agent, search) == NAMESPACE_PUBLIC


async def test_public_agent_lists_public_documents_only() -> None:
    """Scenario: An anonymous visitor's chat lists public documents only"""
    agent, _ = _agent(PUBLIC_KNOWLEDGE)

    listing = await _tool(agent, "list_documents").ainvoke({})

    assert "Public bio" in listing
    assert "Private notes" not in listing
    assert "Carousel source" not in listing


async def test_owner_agent_reads_personal_and_public_knowledge() -> None:
    """Scenario: The owner's chat reads personal and public knowledge"""
    agent, search = _agent(OWNER_KNOWLEDGE)

    assert await _searched_prefix(agent, search) == NAMESPACE_PERSONAL
    listing = await _tool(agent, "list_documents").ainvoke({})
    assert "Public bio" in listing
    assert "Private notes" in listing
    assert "Carousel source" not in listing


async def test_agent_without_a_scope_reads_public_knowledge_only() -> None:
    """Scenario: A chat agent built without a knowledge scope reads public knowledge only"""
    agent = AlterEgoAgent(
        settings=_settings(),
        retriever=AsyncMock(),
        message_repository=AsyncMock(),
        document_repository=_repository(),
    )
    retriever = agent._retriever

    await agent.search_documents("Who are you?")
    listing = await _tool(agent, "list_documents").ainvoke({})

    query: RetrievalQuery = retriever.retrieve.await_args.args[0]
    assert query.namespace_prefix == NAMESPACE_PUBLIC
    assert "Private notes" not in listing
    assert "Public bio" in listing


async def test_owner_agent_direct_search_uses_its_scope() -> None:
    """Scenario: The owner's chat reads personal and public knowledge"""
    agent, _ = _agent(OWNER_KNOWLEDGE)

    await agent.search_documents("Who are you?")

    query: RetrievalQuery = agent._retriever.retrieve.await_args.args[0]
    assert query.namespace_prefix == NAMESPACE_PERSONAL


def _container(site_owner: str) -> MagicMock:
    container = MagicMock()
    container.settings.return_value = Settings(autopilot_owner_user_id=site_owner)
    return container


@pytest.mark.parametrize(
    ("user_id", "site_owner", "expected"),
    [
        (None, str(_SITE_OWNER), PUBLIC_KNOWLEDGE),
        (uuid4(), str(_SITE_OWNER), PUBLIC_KNOWLEDGE),
        (_SITE_OWNER, str(_SITE_OWNER), OWNER_KNOWLEDGE),
        (_SITE_OWNER, "", PUBLIC_KNOWLEDGE),
    ],
    ids=["anonymous", "editor-or-other-admin", "site-owner", "setting-unset"],
)
def test_messages_route_builder_picks_the_scope_from_the_owner(
    user_id: UUID | None, site_owner: str, expected: KnowledgeScope
) -> None:
    """Scenario: Both chat routes pick the scope from the conversation owner"""
    conversation = Conversation(id=uuid4(), user_id=user_id, metadata={})
    db = AsyncMock()
    container = _container(site_owner)

    with patch(_BUILDER) as build_alter_ego:
        build_agent_for_conversation(conversation, db, container)

    build_alter_ego.assert_called_once_with(db, container, expected)


def test_a_search_without_a_namespace_reads_public_only() -> None:
    """Scenario: A search without a namespace reads public knowledge only"""
    assert HybridRetrieverWithRRF._resolve_namespaces(None) == [NAMESPACE_PUBLIC]
