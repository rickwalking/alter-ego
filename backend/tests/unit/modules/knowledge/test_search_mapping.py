"""Boundary mapping shared by the knowledge service and its search port.

Scenario: a search command maps to the domain retrieval query.
Scenario: a retrieval hit maps to a boundary-safe view.
"""

from __future__ import annotations

from rag_backend.modules.knowledge.application.service import (
    to_retrieval_query,
    to_search_view,
)
from rag_backend.modules.knowledge.domain.commands import SearchQuery
from rag_backend.modules.knowledge.domain.models import SearchResult


# Scenario: a search command maps to the domain retrieval query.
def test_search_command_maps_every_field() -> None:
    query = to_retrieval_query(
        SearchQuery(
            query="rag",
            top_k=3,
            alpha=0.2,
            namespace_prefix="docs",
            filters={"lang": "pt"},
        )
    )

    assert (query.query, query.top_k, query.alpha) == ("rag", 3, 0.2)
    assert query.namespace_prefix == "docs"
    assert query.filters == {"lang": "pt"}


# Scenario: a retrieval hit maps to a boundary-safe view.
def test_hit_maps_to_view_with_copied_metadata() -> None:
    hit = SearchResult(
        content="text",
        document_id="d1",
        score=0.9,
        rank=1,
        metadata={"k": "v"},
        chunk_id="c1",
    )

    view = to_search_view(hit)

    assert (view.content, view.document_id, view.score, view.rank) == (
        "text",
        "d1",
        0.9,
        1,
    )
    assert view.chunk_id == "c1"
    assert view.metadata == {"k": "v"}
    assert view.metadata is not hit.metadata
