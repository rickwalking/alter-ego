"""Document processing pipeline service."""

from rag_backend.domain.constants.documents import (
    FAILURE_EMBEDDING_UNAVAILABLE,
    FAILURE_EMPTY_CONTENT,
    FAILURE_PROCESSING_ERROR,
    FAILURE_VECTOR_STORE_UNAVAILABLE,
)
from rag_backend.domain.models import Document, DocumentScope, DocumentStatus
from rag_backend.domain.protocols import (
    DocumentProcessor,
    DocumentRepository,
    VectorStore,
)
from rag_backend.infrastructure.logging import get_logger

PIPELINE_FAILURE_LOGGED = "document pipeline failure already logged as pipeline_failed"
"""Exception note: the pipeline logged this failure with its traceback."""

logger = get_logger()

_ERR_DOCUMENT_NOT_FOUND = "Document with id {} not found"


class DocumentProcessingPipeline:
    """Pipeline for processing documents end-to-end.

    Orchestrates:
    1. Document chunking
    2. Embedding generation
    3. Vector store upsert
    4. Status updates
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        document_processor: DocumentProcessor,
        vector_store: VectorStore,
    ) -> None:
        self._document_repository = document_repository
        self._document_processor = document_processor
        self._vector_store = vector_store

    async def process_document(self, document: Document) -> Document:
        """Process a document through the complete pipeline.

        A failure marks the document failed and re-raises, so an ingest's Unit
        of Work rolls back and nothing partial is persisted.

        Args:
            document: The document to process

        Returns:
            The processed document with updated status
        """
        return await self._run(document, record_failure=False)

    async def _run(self, document: Document, *, record_failure: bool) -> Document:
        """Chunk, embed and upsert; on error mark failed, then raise or return.

        The saved reason is a fixed code naming the step that failed, never the
        error text (provider errors can carry hosts, URLs or key fragments); the
        error itself is only logged.
        """
        reason = FAILURE_PROCESSING_ERROR
        logger.info(
            "pipeline_process_start",
            document_id=str(document.id),
            title=document.title,
            scope=document.scope.value,
        )
        try:
            document.update_status(DocumentStatus.PROCESSING)
            await self._document_repository.update(document)

            reason = FAILURE_EMBEDDING_UNAVAILABLE
            chunks = await self._document_processor.process(document)
            reason = FAILURE_PROCESSING_ERROR

            if not chunks:
                logger.warning("pipeline_no_chunks", document_id=str(document.id))
                document.mark_failed(FAILURE_EMPTY_CONTENT)
                await self._document_repository.update(document)
                return document

            logger.info(
                "pipeline_chunks_generated",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

            namespace = document.scope.value
            reason = FAILURE_VECTOR_STORE_UNAVAILABLE
            await self._vector_store.upsert_chunks(
                chunks, document.id, namespace=namespace
            )
            reason = FAILURE_PROCESSING_ERROR

            document.mark_completed(chunk_count=len(chunks))
            await self._document_repository.update(document)

            logger.info(
                "pipeline_completed",
                document_id=str(document.id),
                chunk_count=len(chunks),
                namespace=namespace,
            )
        except Exception as e:
            logger.exception(
                "pipeline_failed",
                document_id=str(document.id),
                reason=reason,
            )
            e.add_note(PIPELINE_FAILURE_LOGGED)
            document.mark_failed(reason)
            await self._document_repository.update(document)
            if not record_failure:
                raise

        return document

    async def reprocess_document(self, document_id: str) -> Document:
        """Reprocess an existing document.

        Args:
            document_id: ID of the document to reprocess

        Returns:
            The reprocessed document

        Existing chunks are deleted from the current scope's namespace before
        reprocessing. A processing failure is recorded on the document (status
        failed + reason) and returned instead of raised, so the caller's Unit
        of Work commits it and the document never stays pending.
        """
        document = await self._load(document_id)
        await self._vector_store.delete_by_document(
            document.id, namespace=document.scope.value
        )
        return await self._restart(document)

    async def rescope_document(
        self, document_id: str, scope: DocumentScope
    ) -> Document:
        """Move a document to another scope and re-index it there.

        The chunks are deleted from the old scope's namespace, the document
        takes the new scope (public only for the public scope) and is processed
        again into the new namespace. A failure is recorded like a reprocess.
        """
        document = await self._load(document_id)
        await self._vector_store.delete_by_document(
            document.id, namespace=document.scope.value
        )
        document.scope = scope
        document.is_public = scope is DocumentScope.PUBLIC
        return await self._restart(document)

    async def drop_chunks(self, document_id: str, scope: DocumentScope) -> None:
        """Delete the document's chunks from the namespace of ``scope``."""
        from uuid import UUID

        await self._vector_store.delete_by_document(
            UUID(document_id), namespace=scope.value
        )

    async def _load(self, document_id: str) -> Document:
        """The stored document, or ``ValueError`` when it does not exist."""
        from uuid import UUID

        document = await self._document_repository.get_by_id(UUID(document_id))
        if not document:
            raise ValueError(_ERR_DOCUMENT_NOT_FOUND.format(document_id))
        return document

    async def _restart(self, document: Document) -> Document:
        """Reset the document to pending and run the pipeline, recording a failure."""
        document.update_status(DocumentStatus.PENDING)
        document.error_message = None
        document.chunk_count = 0
        await self._document_repository.update(document)

        return await self._run(document, record_failure=True)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its vectors.

        Args:
            document_id: ID of the document to delete

        Returns:
            True if deleted successfully

        The vector-store chunks are deleted before the database row.
        """
        from uuid import UUID

        doc_id = UUID(document_id)

        document = await self._document_repository.get_by_id(doc_id)
        namespace = document.scope.value if document else None

        await self._vector_store.delete_by_document(doc_id, namespace=namespace)

        return await self._document_repository.delete(doc_id)

    def estimate_processing_time(self, document: Document) -> dict[str, object]:
        """Estimate processing time for a document.

        Returns:
            Dictionary with estimates

        The estimates are rough per-chunk costs: 10 ms chunking, 100 ms embedding and 5
        ms upsert.
        """
        estimated_chunks = self._document_processor.estimate_chunks(document.content)

        chunking_time = estimated_chunks * 0.01
        embedding_time = estimated_chunks * 0.1
        upsert_time = estimated_chunks * 0.005

        total_time = chunking_time + embedding_time + upsert_time

        return {
            "estimated_chunks": estimated_chunks,
            "chunking_time_seconds": round(chunking_time, 2),
            "embedding_time_seconds": round(embedding_time, 2),
            "upsert_time_seconds": round(upsert_time, 2),
            "total_time_seconds": round(total_time, 2),
        }
