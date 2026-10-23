"""Application service (use case entry point) for the knowledge module.

Private to the module — the public facade re-exports it under
``KnowledgeService``; cross-module code never imports this path directly.

This is a **behavior-preserving** facade over the existing knowledge
collaborators: the document repository, the document-processing
pipeline, and the hybrid retriever. It introduces no new behavior — each method
maps a typed command/query onto the same calls the legacy routes make today,
so ``/api/documents`` and ``/api/search`` stay byte-identical when they move
behind the facade.

Dependencies are injected through the constructor (manual constructor
injection, ADR-0009 §9). The request-scoped Unit of Work is owned at the
inbound (api) edge and the request-scoped repository is injected by
``bootstrap_module``; this service does not resolve a global container.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID

from rag_backend.modules.knowledge.api.views import (
    DocumentStatusView,
    KnowledgeDocumentListView,
    KnowledgeDocumentView,
    SearchResultView,
)
from rag_backend.modules.knowledge.domain.commands import (
    ChangeDocumentScopeCommand,
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
    DocumentScope,
    KnowledgeDocument,
    RetrievalQuery,
    SearchResult,
)
from rag_backend.modules.knowledge.domain.ports import (
    DocumentRepository,
    OwnerDocumentQuery,
)
from rag_backend.platform.database import UnitOfWork

_ESTIMATED_CHUNKS_KEY = "estimated_chunks"
_TOTAL_TIME_KEY = "total_time_seconds"
_OWNER_ID_REQUIRED = "owner_id is required for a non-admin document listing"


class DocumentPipelinePort(Protocol):
    """Pipeline operations the knowledge use cases delegate to.

    Matches the existing ``DocumentProcessingPipeline`` shape so the module
    wires to the legacy adapter without behavior change.
    """

    async def process_document(
        self, document: KnowledgeDocument
    ) -> KnowledgeDocument: ...

    async def reprocess_document(self, document_id: str) -> KnowledgeDocument: ...

    async def rescope_document(
        self, document_id: str, scope: DocumentScope
    ) -> KnowledgeDocument: ...

    async def drop_chunks(self, document_id: str, scope: DocumentScope) -> None: ...

    async def delete_document(self, document_id: str) -> bool: ...

    def estimate_processing_time(
        self, document: KnowledgeDocument
    ) -> dict[str, object]: ...


class RetrieverPort(Protocol):
    """Retrieval operation the search use case delegates to.

    Matches the existing ``HybridRetrieverWithRRF.retrieve`` shape (distinct
    from the shared ``Retriever.search`` port) so the module wires to the
    legacy adapter without behavior change.
    """

    async def retrieve(self, request: RetrievalQuery) -> list[SearchResult]: ...


@dataclass(frozen=True)
class KnowledgeServiceDeps:
    """Collaborators grouped to keep the service constructor at ≤3 arguments.

    Bundles the retrieval adapter and the request-scoped Unit of Work so the
    repository and pipeline stay explicit while the constructor honours the
    backend/CLAUDE.md 3-argument limit.
    """

    retriever: RetrieverPort
    unit_of_work: UnitOfWork


class KnowledgeService:
    """Use-case entry point for the knowledge bounded context.

    Write use cases (``create``/``ingest``/``delete``/``reprocess``) run under
    the injected request-scoped Unit of Work, which is the **single commit
    owner** (ADR-0009): repositories only flush, and this service commits once
    via the UoW at the end of a successful write, or rolls back with no partial
    writes if it raises. Read use cases do not commit.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        pipeline: DocumentPipelinePort,
        deps: KnowledgeServiceDeps,
    ) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._retriever = deps.retriever
        self._unit_of_work = deps.unit_of_work

    async def create(self, command: CreateDocumentCommand) -> KnowledgeDocumentView:
        """Create a document without immediate processing (committed once)."""
        async with self._unit_of_work:
            created = await self._repository.create(self._build_document(command))
            view = self._to_view(created)
        return view

    async def ingest(self, command: IngestDocumentCommand) -> KnowledgeDocumentView:
        """Create a document and run the full pipeline (committed once).

        The create and the pipeline run inside one Unit of Work: if the pipeline
        raises (e.g. during embedding), the UoW rolls back and no partial
        document or chunks are persisted (Gherkin: failed ingest rolls back).
        """
        async with self._unit_of_work:
            created = await self._repository.create(self._build_document(command))
            processed = await self._pipeline.process_document(created)
            view = self._to_view(processed)
        return view

    async def list_documents(
        self, query: ListDocumentsQuery
    ) -> list[KnowledgeDocumentView]:
        """List documents with optional status filter and paging.

        Named ``list_documents`` (not ``list``) to avoid shadowing the builtin
        ``list`` used in return annotations elsewhere on this class; it is the
        facade's "list" operation.
        """
        documents = await self._repository.get_all(
            status=query.status, limit=query.limit, offset=query.offset
        )
        return [self._to_view(document) for document in documents]

    async def list_with_total(
        self, query: ListDocumentsQuery
    ) -> KnowledgeDocumentListView:
        """List a page of documents plus the matching total, scoped by access.

        Admin queries (``is_admin=True``) list across all owners; otherwise the
        listing is restricted to ``owner_id``. Mirrors the legacy
        ``/api/documents`` listing (owner-vs-admin split + ``total``) exactly.
        """
        if query.is_admin:
            return await self._list_all(query)
        return await self._list_for_owner(query)

    async def _list_all(self, query: ListDocumentsQuery) -> KnowledgeDocumentListView:
        documents = await self._repository.get_all(
            status=query.status, limit=query.limit, offset=query.offset
        )
        total = await self._repository.count(status=query.status)
        return KnowledgeDocumentListView(
            items=[self._to_view(document) for document in documents],
            total=total,
        )

    async def _list_for_owner(
        self, query: ListDocumentsQuery
    ) -> KnowledgeDocumentListView:
        owner_id = self._require_owner_id(query.owner_id)
        documents = await self._repository.get_all_for_owner(
            OwnerDocumentQuery(
                owner_id=owner_id,
                status=query.status,
                limit=query.limit,
                offset=query.offset,
            )
        )
        total = await self._repository.count_for_owner(
            owner_id=owner_id, status=query.status
        )
        return KnowledgeDocumentListView(
            items=[self._to_view(document) for document in documents],
            total=total,
        )

    @staticmethod
    def _require_owner_id(owner_id: UUID | None) -> UUID:
        if owner_id is None:
            raise ValueError(_OWNER_ID_REQUIRED)
        return owner_id

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
        """Delete a document and its vectors (committed once)."""
        async with self._unit_of_work:
            deleted = await self._pipeline.delete_document(str(command.document_id))
        return deleted

    async def reprocess(
        self, command: ReprocessDocumentCommand
    ) -> KnowledgeDocumentView:
        """Re-run the pipeline for an existing document (committed once).

        The document row is locked first, so a concurrent scope change waits
        instead of indexing the chunks into a namespace this run is leaving.
        """
        async with self._unit_of_work:
            await self._repository.get_by_id_for_update(command.document_id)
            document = await self._pipeline.reprocess_document(str(command.document_id))
            view = self._to_view(document)
        return view

    async def change_scope(
        self, command: ChangeDocumentScopeCommand
    ) -> KnowledgeDocumentView | None:
        """Move a document to ``command.scope`` (committed once), or ``None`` if absent.

        A document already in that scope is returned as it is, without
        re-indexing. The row is locked for the whole move. When anything fails
        after the re-index (the commit included), the chunks written to the new
        scope's namespace are deleted again, so a rolled-back move never leaves
        the document searchable under the scope it did not get.
        """
        reindexed = False
        try:
            async with self._unit_of_work:
                document = await self._repository.get_by_id_for_update(
                    command.document_id
                )
                if document is None:
                    return None
                if document.scope is command.scope:
                    return self._to_view(document)
                reindexed = True
                moved = await self._pipeline.rescope_document(
                    str(command.document_id), command.scope
                )
                view = self._to_view(moved)
        except Exception:
            if reindexed:
                await self._pipeline.drop_chunks(
                    str(command.document_id), command.scope
                )
            raise
        return view

    async def search(self, query: SearchQuery) -> list[SearchResultView]:
        """Hybrid-search the knowledge base."""
        results = await self._retriever.retrieve(to_retrieval_query(query))
        return [to_search_view(result) for result in results]

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


def to_retrieval_query(query: SearchQuery) -> RetrievalQuery:
    """The domain retrieval request for one boundary search command."""
    return RetrievalQuery(
        query=query.query,
        top_k=query.top_k,
        alpha=query.alpha,
        filters=query.filters,
        namespace_prefix=query.namespace_prefix,
    )


def to_search_view(result: SearchResult) -> SearchResultView:
    """The boundary-safe projection of one retrieval hit."""
    return SearchResultView(
        content=result.content,
        document_id=result.document_id,
        score=result.score,
        rank=result.rank,
        metadata=dict(result.metadata),
        chunk_id=result.chunk_id,
    )
