"""Typed command and query objects for the knowledge bounded context.

These are the boundary-safe, statically-typed inputs the facade accepts —
no arbitrary ``dict`` bundles and no ``Any`` (backend/CLAUDE.md). One object
per facade operation (ingest/create/list/get/status/delete/reprocess/search),
so the use-case entry points keep to a single grouped argument and stay under
the 3-argument limit.

They carry intent only; they are not persistence rows. The application service
maps them onto the existing ``Document`` aggregate and pipeline during the
behavior-preserving phase (AE-0089).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from rag_backend.modules.knowledge.domain.models import (
    DocumentScope,
    DocumentStatus,
)

# Boundary-safe metadata value type (mirrors the Document.metadata shape).
MetadataValue = str | int | float | bool


@dataclass(frozen=True)
class CreateDocumentCommand:
    """Create a knowledge document without immediate processing."""

    title: str
    content: str
    owner_id: UUID | None = None
    scope: DocumentScope = DocumentScope.PERSONAL
    is_public: bool = False
    metadata: dict[str, MetadataValue] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestDocumentCommand:
    """Create a knowledge document and run it through the full pipeline.

    Same shape as :class:`CreateDocumentCommand`; distinct type so the facade
    can express "create + process" as its own use case (used by the upload
    path) versus a bare create.
    """

    title: str
    content: str
    owner_id: UUID | None = None
    scope: DocumentScope = DocumentScope.PERSONAL
    is_public: bool = False
    metadata: dict[str, MetadataValue] = field(default_factory=dict)


@dataclass(frozen=True)
class ListDocumentsQuery:
    """List knowledge documents with optional status filter and paging.

    Access scope is expressed by ``owner_id`` + ``is_admin``: an admin query
    (``is_admin=True``) lists across all owners; otherwise the listing is
    restricted to ``owner_id``. Both default to the unrestricted/admin-less
    case so existing callers keep their behavior.
    """

    status: DocumentStatus | None = None
    limit: int = 100
    offset: int = 0
    owner_id: UUID | None = None
    is_admin: bool = False


@dataclass(frozen=True)
class GetDocumentQuery:
    """Fetch a single knowledge document by id."""

    document_id: UUID


@dataclass(frozen=True)
class DocumentStatusQuery:
    """Fetch processing status/estimates for a knowledge document."""

    document_id: UUID


@dataclass(frozen=True)
class DeleteDocumentCommand:
    """Delete a knowledge document and its vectors."""

    document_id: UUID


@dataclass(frozen=True)
class ReprocessDocumentCommand:
    """Re-run the pipeline for an existing knowledge document."""

    document_id: UUID


@dataclass(frozen=True)
class SearchQuery:
    """Hybrid-search the knowledge base."""

    query: str
    top_k: int = 5
    alpha: float = 0.5
    namespace_prefix: str | None = None
    filters: dict[str, MetadataValue] | None = None


__all__ = [
    "CreateDocumentCommand",
    "DeleteDocumentCommand",
    "DocumentStatusQuery",
    "GetDocumentQuery",
    "IngestDocumentCommand",
    "ListDocumentsQuery",
    "MetadataValue",
    "ReprocessDocumentCommand",
    "SearchQuery",
]
