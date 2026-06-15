"""Knowledge bounded context (Supporting) — AE-0089 Phase 2 skeleton.

The knowledge context owns document ingestion, storage, processing, and hybrid
search. This package follows the module conventions
(``docs/architecture/module-conventions.md``, AE-0081) and ADR-0009 (Domain
Modular Monolith):

* per-module internal layers — ``domain/``, ``application/``,
  ``infrastructure/``, ``api/``;
* the **public-facade rule** — cross-module code imports ONLY from this
  package's public API (``public.py``, re-exported here);
* manual constructor injection via ``bootstrap_module`` (ADR-0009 §9);
* the Unit-of-Work boundary owned at the application layer.

Phase 2 is **behavior-preserving** (AE-0089): the five ports and the document
aggregate are *re-exported* from their legacy locations (no physical move), the
infrastructure adapters are not relocated, and ``/api/documents`` /
``/api/search`` are unchanged. Routes move behind this facade in AE-0092/0093.

Cross-module consumers SHALL import from the facade only, e.g.::

    from rag_backend.modules.knowledge import KnowledgeService, SearchQuery
"""

from rag_backend.modules.knowledge.public import (
    CreateDocumentCommand,
    DeleteDocumentCommand,
    DocumentStatusQuery,
    DocumentStatusView,
    GetDocumentQuery,
    IngestDocumentCommand,
    KnowledgeAdapters,
    KnowledgeDocument,
    KnowledgeDocumentListView,
    KnowledgeDocumentView,
    KnowledgeService,
    ListDocumentsQuery,
    ReprocessDocumentCommand,
    SearchQuery,
    SearchResultView,
    bootstrap_module,
)

__all__ = [
    "CreateDocumentCommand",
    "DeleteDocumentCommand",
    "DocumentStatusQuery",
    "DocumentStatusView",
    "GetDocumentQuery",
    "IngestDocumentCommand",
    "KnowledgeAdapters",
    "KnowledgeDocument",
    "KnowledgeDocumentListView",
    "KnowledgeDocumentView",
    "KnowledgeService",
    "ListDocumentsQuery",
    "ReprocessDocumentCommand",
    "SearchQuery",
    "SearchResultView",
    "bootstrap_module",
]
