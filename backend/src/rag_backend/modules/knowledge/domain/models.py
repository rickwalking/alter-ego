"""Domain entities and value objects for the knowledge bounded context.

Phase 2 is a **behavior-preserving** extraction (ADR-0009; AE-0089). The
knowledge aggregate and its value objects continue to live at their legacy
location ``rag_backend.domain.models.documents`` so the ~50+ existing callers
(agents, carousel, conversation, container, routes) keep importing the exact
same objects. This module **re-exports** them under the module's domain
namespace and aliases the document aggregate as ``KnowledgeDocument``.

Physical relocation of these entities into the module is deferred to a later
phase. Until then ``KnowledgeDocument`` is the same class object as
``Document`` (a re-export, not a wrapper), so identity/isinstance checks and
the existing persistence adapters keep working unchanged.
"""

from __future__ import annotations

from rag_backend.domain.models.documents import (
    Document,
    DocumentChunk,
    DocumentScope,
    DocumentStatus,
    HybridSearchParams,
    RetrievalQuery,
    SearchResult,
)

# The knowledge aggregate. Same class object as ``Document`` so existing
# callers and adapters remain compatible during the behavior-preserving phase.
KnowledgeDocument = Document

__all__ = [
    "Document",
    "DocumentChunk",
    "DocumentScope",
    "DocumentStatus",
    "HybridSearchParams",
    "KnowledgeDocument",
    "RetrievalQuery",
    "SearchResult",
]
