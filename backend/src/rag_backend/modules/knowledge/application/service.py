"""Application service (use case entry point) for the knowledge module.

Private to the module — the public facade re-exports it under
``KnowledgeService``; cross-module code never imports this path directly.

This is a **behavior-preserving** facade over the existing knowledge
collaborators (AE-0089): the document repository, the document-processing
pipeline, and the hybrid retriever. It introduces no new behavior — each method
maps a typed command/query onto the same calls the legacy routes make today,
so ``/api/documents`` and ``/api/search`` stay byte-identical when they move
behind the facade (AE-0092/0093).

Dependencies are injected through the constructor (manual constructor
injection, ADR-0009 §9). The request-scoped Unit of Work is owned at the
inbound (api) edge and the request-scoped repository is injected by
``bootstrap_module``; this service does not resolve a global container.
"""

from __future__ import annotations

from typing import Protocol, cast

from rag_backend.modules.knowledge.api.views import (
    DocumentStatusView,
    KnowledgeDocumentView,
    SearchResultView,
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
from rag_backend.modules.knowledge.domain.models import (
    KnowledgeDocument,
    RetrievalQuery,
    SearchResult,
)
from rag_backend.modules.knowledge.domain.ports import DocumentRepository

_ESTIMATED_CHUNKS_KEY = "estimated_chunks"
_TOTAL_TIME_KEY = "total_time_seconds"


class DocumentPipelinePort(Protocol):
    """Pipeline operations the knowledge use cases delegate to.

    Matches the existing ``DocumentProcessingPipeline`` shape so the module
    wires to the legacy adapter without behavior change (AE-0089).
    """

    async def process_document(
        self, document: KnowledgeDocument
    ) -> KnowledgeDocument: ...

    async def reprocess_document(self, document_id: str) -> KnowledgeDocument: ...

    async def delete_document(self, document_id: str) -> bool: ...

    def estimate_processing_time(
        self, document: KnowledgeDocument
    ) -> dict[str, object]: ...


class RetrieverPort(Protocol):
    """Retrieval operation the search use case delegates to.

    Matches the existing ``HybridRetrieverWithRRF.retrieve`` shape (distinct
    from the shared ``Retriever.search`` port) so the module wires to the
    legacy adapter without behavior change (AE-0089).
    """

    async def retrieve(self, request: RetrievalQuery) -> list[SearchResult]: ...


class KnowledgeService:
    """Use-case entry point for the knowledge bounded context."""

    def __init__(
        self,
        repository: DocumentRepository,
        pipeline: DocumentPipelinePort,
        retriever: RetrieverPort,
    ) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._retriever = retriever

    async def create(self, command: CreateDocumentCommand) -> KnowledgeDocumentView:
        """Create a document without immediate processing."""
        created = await self._repository.create(self._build_document(command))
        return self._to_view(created)

    async def ingest(self, command: IngestDocumentCommand) -> KnowledgeDocumentView:
        """Create a document and run it through the full pipeline."""
        created = await self._repository.create(self._build_document(command))
        processed = await self._pipeline.process_document(created)
        return self._to_view(processed)

    async def list_documents(
        self, query: ListDocumentsQuery
    ) -> list[KnowledgeDocumentView]:
        """List documents with optional status filter and paging.

        Named ``list_documents`` (not ``list``) to avoid shadowing the builtin
        ``list`` used in return annotations elsewhere on this class; it is the
        facade's "list" operation (AE-0089 AC).
        """
        documents = await self._repository.get_all(
            status=query.status, limit=query.limit, offset=query.offset
        )
        return [self._to_view(document) for document in documents]

    async def get(self, query: GetDocumentQuery) -> KnowledgeDocumentView | None:
        """Fetch a single document by id, or ``None`` if absent."""
        document = await self._repository.get_by_id(query.document_id)
        if document is None:
            return None
        return self._to_view(document)

    async def status(self, query: DocumentStatusQuery) -> DocumentStatusView | None:
        """Fetch processing status + estimates, or ``None`` if absent."""
        document = await self._repository.get_by_id(query.document_id)
        if document is None:
            return None
        estimates = self._pipeline.estimate_processing_time(document)
        return DocumentStatusView(
            id=document.id,
            status=document.status.value,
            chunk_count=document.chunk_count,
            estimated_chunks=cast(int, estimates[_ESTIMATED_CHUNKS_KEY]),
            estimated_time_seconds=cast(float, estimates[_TOTAL_TIME_KEY]),
        )

    async def delete(self, command: DeleteDocumentCommand) -> bool:
        """Delete a document and its vectors."""
        return await self._pipeline.delete_document(str(command.document_id))

    async def reprocess(
        self, command: ReprocessDocumentCommand
    ) -> KnowledgeDocumentView:
        """Re-run the pipeline for an existing document."""
        document = await self._pipeline.reprocess_document(str(command.document_id))
        return self._to_view(document)

    async def search(self, query: SearchQuery) -> list[SearchResultView]:
        """Hybrid-search the knowledge base."""
        results = await self._retriever.retrieve(
            RetrievalQuery(
                query=query.query,
                top_k=query.top_k,
                alpha=query.alpha,
                filters=query.filters,
                namespace_prefix=query.namespace_prefix,
            )
        )
        return [self._to_search_view(result) for result in results]

    @staticmethod
    def _build_document(
        command: CreateDocumentCommand | IngestDocumentCommand,
    ) -> KnowledgeDocument:
        return KnowledgeDocument(
            title=command.title,
            content=command.content,
            metadata=dict(command.metadata),
            scope=command.scope,
            is_public=command.is_public,
            owner_id=command.owner_id,
        )

    @staticmethod
    def _to_view(document: KnowledgeDocument) -> KnowledgeDocumentView:
        return KnowledgeDocumentView(
            id=document.id,
            title=document.title,
            status=document.status.value,
            scope=document.scope.value,
            chunk_count=document.chunk_count,
            is_public=document.is_public,
            created_at=document.created_at,
            updated_at=document.updated_at,
            owner_id=document.owner_id,
            error_message=document.error_message,
            metadata=dict(document.metadata),
        )

    @staticmethod
    def _to_search_view(result: SearchResult) -> SearchResultView:
        return SearchResultView(
            content=result.content,
            document_id=result.document_id,
            score=result.score,
            rank=result.rank,
            metadata=dict(result.metadata),
            chunk_id=result.chunk_id,
        )
