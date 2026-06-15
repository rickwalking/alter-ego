"""Public facade for the knowledge bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.knowledge.*`` is private to the
module. The dedicated Import Linter facade contract is added in AE-0095.

The facade exposes:

* ``KnowledgeService`` — the use-case entry point with the
  ingest/create/list/get/status/delete/reprocess/search operations;
* the typed **command/query** objects those operations accept;
* the boundary-safe **view** DTOs they return;
* ``KnowledgeDocument`` — the aggregate (re-exported ``Document``) so existing
  ``domain/models`` callers keep a stable name during the behavior-preserving
  phase;
* ``KnowledgeAdapters`` + ``bootstrap_module`` — the composition root (manual
  constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.knowledge.application.service`` or
``rag_backend.modules.knowledge.domain.models`` directly.
"""

from rag_backend.modules.knowledge.api.views import (
    DocumentStatusView,
    KnowledgeDocumentListView,
    KnowledgeDocumentView,
    SearchResultView,
)
from rag_backend.modules.knowledge.application.search_port import (
    KnowledgeSearchPort,
    RetrieverSearchAdapter,
)
from rag_backend.modules.knowledge.application.service import KnowledgeService
from rag_backend.modules.knowledge.bootstrap import (
    KnowledgeAdapters,
    bootstrap_module,
)
from rag_backend.modules.knowledge.domain.commands import (
    CreateDocumentCommand,
    DeleteDocumentCommand,
    DocumentStatusQuery,
    GetDocumentQuery,
    IngestDocumentCommand,
    ListDocumentsQuery,
    ReprocessDocumentCommand,
    SearchQuery,
)
from rag_backend.modules.knowledge.domain.models import KnowledgeDocument

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
    "KnowledgeSearchPort",
    "KnowledgeService",
    "ListDocumentsQuery",
    "ReprocessDocumentCommand",
    "RetrieverSearchAdapter",
    "SearchQuery",
    "SearchResultView",
    "bootstrap_module",
]
