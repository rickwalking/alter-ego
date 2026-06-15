"""Domain layer for the knowledge bounded context (private to the module).

Exposes the knowledge aggregate (``KnowledgeDocument``), its value objects,
the five outbound ports, and the typed command/query objects. Cross-module
consumers do NOT import this subpackage directly — they use the module facade
(``rag_backend.modules.knowledge``). This ``__init__`` is an intra-module
convenience for the application/infrastructure/api layers.
"""

from rag_backend.modules.knowledge.domain.commands import (
    CreateDocumentCommand,
    DeleteDocumentCommand,
    DocumentStatusQuery,
    GetDocumentQuery,
    IngestDocumentCommand,
    ListDocumentsQuery,
    MetadataValue,
    ReprocessDocumentCommand,
    SearchQuery,
)
from rag_backend.modules.knowledge.domain.models import (
    Document,
    DocumentChunk,
    DocumentScope,
    DocumentStatus,
    HybridSearchParams,
    KnowledgeDocument,
    RetrievalQuery,
    SearchResult,
)
from rag_backend.modules.knowledge.domain.ports import (
    DocumentProcessor,
    DocumentRepository,
    EmbeddingService,
    Retriever,
    VectorStore,
)

__all__ = [
    "CreateDocumentCommand",
    "DeleteDocumentCommand",
    "Document",
    "DocumentChunk",
    "DocumentProcessor",
    "DocumentRepository",
    "DocumentScope",
    "DocumentStatus",
    "DocumentStatusQuery",
    "EmbeddingService",
    "GetDocumentQuery",
    "HybridSearchParams",
    "IngestDocumentCommand",
    "KnowledgeDocument",
    "ListDocumentsQuery",
    "MetadataValue",
    "ReprocessDocumentCommand",
    "RetrievalQuery",
    "Retriever",
    "SearchQuery",
    "SearchResult",
    "VectorStore",
]
