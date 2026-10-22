"""Knowledge search port + a retriever-backed adapter.

The **search port** is the boundary-safe contract the agent search tool and the
``/api/search`` route depend on: a single ``search(SearchQuery) ->
list[SearchResultView]`` operation. ``KnowledgeService`` satisfies it, so inbound
adapters obtain hybrid search through the module's public facade instead of
wiring a raw retriever that bypasses the module.

``RetrieverSearchAdapter`` bridges the existing ``RetrieverPort`` (the legacy
``HybridRetrieverWithRRF.retrieve`` shape) onto the search port. It applies the
exact same mapping ``KnowledgeService.search`` does (``SearchQuery`` ->
``RetrievalQuery`` -> ``SearchResultView``), so search behavior is identical
whether callers use the full ``KnowledgeService`` facade or this search-only
adapter. The adapter stays free of SQLAlchemy/Pinecone imports — it only knows
the retriever port shape and the module's own domain/view types.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules.knowledge.api.views import SearchResultView
from rag_backend.modules.knowledge.application.service import (
    RetrieverPort,
    to_retrieval_query,
    to_search_view,
)
from rag_backend.modules.knowledge.domain.commands import SearchQuery


class KnowledgeSearchPort(Protocol):
    """Hybrid-search contract exposed across the knowledge module boundary.

    Implemented by ``KnowledgeService`` (the full facade) and by
    ``RetrieverSearchAdapter`` (a search-only view over a retriever). Inbound
    adapters (the ``/api/search`` route, the agent search tool) depend on this
    port so they never reach past the module to a raw retriever.
    """

    async def search(self, query: SearchQuery) -> list[SearchResultView]: ...


class RetrieverSearchAdapter:
    """Adapt a ``RetrieverPort`` to the :class:`KnowledgeSearchPort`.

    Mirrors ``KnowledgeService.search`` exactly so the search-only path (the
    agent search tool, where the full service's repository/pipeline/UoW are not
    needed) returns identical results to the route path.
    """

    def __init__(self, retriever: RetrieverPort) -> None:
        self._retriever = retriever

    async def search(self, query: SearchQuery) -> list[SearchResultView]:
        results = await self._retriever.retrieve(to_retrieval_query(query))
        return [to_search_view(result) for result in results]


__all__ = [
    "KnowledgeSearchPort",
    "RetrieverSearchAdapter",
]
