"""Public view DTOs exposed across the knowledge module boundary.

These boundary-safe shapes are what other modules and inbound adapters consume
via the facade. They decouple consumers from the module's internal aggregate
(``KnowledgeDocument`` / ``Document``).

During the behavior-preserving phase (AE-0089) the HTTP routes still return the
legacy ``Document`` entity directly via their FastAPI ``response_model``; these
views are the boundary contract the routes adopt when they move behind the
facade (AE-0092/0093). The facade also returns the aggregate where a route
needs the legacy shape, so this phase introduces no response change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from rag_backend.modules.knowledge.domain.commands import MetadataValue


@dataclass(frozen=True)
class KnowledgeDocumentView:
    """Boundary-safe projection of a knowledge document."""

    id: UUID
    title: str
    status: str
    scope: str
    chunk_count: int
    is_public: bool
    created_at: datetime
    updated_at: datetime
    owner_id: UUID | None = None
    error_message: str | None = None
    metadata: dict[str, MetadataValue] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeDocumentListView:
    """Boundary-safe page of knowledge documents plus the matching total.

    ``items`` is the requested page; ``total`` is the full count for the same
    filter (used by callers for pagination). Mirrors the legacy list endpoint's
    ``items``/``total`` contract.
    """

    items: list[KnowledgeDocumentView]
    total: int


@dataclass(frozen=True)
class DocumentStatusView:
    """Boundary-safe processing status + estimates for a document."""

    id: UUID
    status: str
    chunk_count: int
    estimated_chunks: int
    estimated_time_seconds: float


@dataclass(frozen=True)
class SearchResultView:
    """Boundary-safe projection of a single search hit."""

    content: str
    document_id: UUID
    score: float
    rank: int
    metadata: dict[str, MetadataValue] = field(default_factory=dict)
    chunk_id: UUID | None = None


__all__ = [
    "DocumentStatusView",
    "KnowledgeDocumentListView",
    "KnowledgeDocumentView",
    "SearchResultView",
]
