"""The public chat agent, over the real retriever and store, returns public knowledge only.

The index really holds one personal chunk and one public chunk; the agent's
search and list tools run end to end through ``HybridRetrieverWithRRF`` and
``PineconeVectorStore``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from langchain_core.tools import BaseTool

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.chat_knowledge import (
    OWNER_KNOWLEDGE,
    PUBLIC_KNOWLEDGE,
    ChatKnowledge,
    KnowledgeScope,
)
from rag_backend.domain.constants.namespaces import NAMESPACE_PERSONAL, NAMESPACE_PUBLIC
from rag_backend.domain.models import Document, DocumentScope, DocumentStatus
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.retrieval.hybrid_retriever import (
    HybridRetrieverWithRRF,
)
from tests.pinecone_index_fakes import FakePineconeIndex, store_over

_PERSONAL_TEXT = "Pedro's private salary notes"
_PUBLIC_TEXT = "Pedro's public bio"


class _Embeddings:
    async def embed_dense(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] for _ in texts]

    async def embed_sparse(self, texts: list[str]) -> list[dict[str, list[float]]]:
        return [{"indices": [], "values": []} for _ in texts]


def _document(title: str, scope: DocumentScope) -> Document:
    return Document(
        content=title,
        title=title,
        scope=scope,
        is_public=scope is DocumentScope.PUBLIC,
        status=DocumentStatus.COMPLETED,
        chunk_count=1,
    )


def _settings() -> MagicMock:
    settings = MagicMock(spec=Settings)
    settings.anthropic_api_key = "test"
    settings.anthropic_model = "claude-test"
    settings.llm_provider = "anthropic"
    return settings


def _agent(scope: KnowledgeScope) -> AlterEgoAgent:
    personal = _document(_PERSONAL_TEXT, DocumentScope.PERSONAL)
    public = _document(_PUBLIC_TEXT, DocumentScope.PUBLIC)
    index = FakePineconeIndex()
    index.seed_chunk(personal.id, NAMESPACE_PERSONAL, _PERSONAL_TEXT)
    index.seed_chunk(public.id, NAMESPACE_PUBLIC, _PUBLIC_TEXT)
    retriever = HybridRetrieverWithRRF(store_over(index), _Embeddings())
    repository = AsyncMock()
    repository.get_all = AsyncMock(return_value=[personal, public])
    return AlterEgoAgent(
        settings=_settings(),
        retriever=retriever,
        message_repository=AsyncMock(),
        document_repository=repository,
        knowledge=ChatKnowledge(scope=scope),
    )


def _tool(agent: AlterEgoAgent, name: str) -> BaseTool:
    return next(t for t in agent._build_tools() if t.name.lstrip("_") == name)


async def test_public_agent_search_returns_only_the_public_chunk() -> None:
    """Scenario: The public scope returns only public knowledge from the index"""
    agent = _agent(PUBLIC_KNOWLEDGE)

    found = await _tool(agent, "search_documents").ainvoke({"query": "Pedro"})
    direct = await agent.search_documents("Pedro")

    assert _PUBLIC_TEXT in found
    assert _PERSONAL_TEXT not in found
    assert [result.content for result in direct] == [_PUBLIC_TEXT]


async def test_public_agent_lists_only_the_public_document() -> None:
    """Scenario: The public scope returns only public knowledge from the index"""
    listing = await _tool(_agent(PUBLIC_KNOWLEDGE), "list_documents").ainvoke({})

    assert _PUBLIC_TEXT in listing
    assert _PERSONAL_TEXT not in listing


async def test_owner_agent_reaches_both_chunks() -> None:
    """Scenario: The owner's chat reads personal and public knowledge"""
    agent = _agent(OWNER_KNOWLEDGE)

    direct = await agent.search_documents("Pedro")

    assert {result.content for result in direct} == {_PERSONAL_TEXT, _PUBLIC_TEXT}
    assert all(isinstance(result.document_id, UUID) for result in direct)
