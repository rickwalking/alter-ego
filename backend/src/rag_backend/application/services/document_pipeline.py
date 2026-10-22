"""Document processing pipeline service."""

from rag_backend.domain.models import Document, DocumentStatus
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
_MAX_FAILURE_REASON_CHARS = 300


def _failure_reason(error: Exception) -> str:
    """A short, typed reason for a failed processing run (stored on the row)."""
    reason = f"{type(error).__name__}: {error}"
    return reason[:_MAX_FAILURE_REASON_CHARS]


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
        """Chunk, embed and upsert; on error mark failed, then raise or return."""
        logger.info(
            "pipeline_process_start",
            document_id=str(document.id),
            title=document.title,
            scope=document.scope.value,
        )
        try:
            document.update_status(DocumentStatus.PROCESSING)
            await self._document_repository.update(document)

            chunks = await self._document_processor.process(document)

            if not chunks:
                logger.warning("pipeline_no_chunks", document_id=str(document.id))
                document.mark_failed("No chunks generated from document")
                await self._document_repository.update(document)
                return document

            logger.info(
                "pipeline_chunks_generated",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

            namespace = document.scope.value
            await self._vector_store.upsert_chunks(
                chunks, document.id, namespace=namespace
            )

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
            )
            e.add_note(PIPELINE_FAILURE_LOGGED)
            document.mark_failed(_failure_reason(e))
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
        from uuid import UUID

        document = await self._document_repository.get_by_id(UUID(document_id))
        if not document:
            raise ValueError(_ERR_DOCUMENT_NOT_FOUND.format(document_id))

        await self._vector_store.delete_by_document(
            document.id, namespace=document.scope.value
        )

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
