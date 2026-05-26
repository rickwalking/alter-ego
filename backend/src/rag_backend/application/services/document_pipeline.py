"""Document processing pipeline service."""

from rag_backend.domain.models import Document, DocumentStatus
from rag_backend.domain.protocols import (
    DocumentProcessor,
    DocumentRepository,
    VectorStore,
)

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

        Args:
            document: The document to process

        Returns:
            The processed document with updated status
        """
        try:
            # Update status to processing
            document.update_status(DocumentStatus.PROCESSING)
            await self._document_repository.update(document)

            # Process document into chunks with embeddings
            chunks = await self._document_processor.process(document)

            if not chunks:
                document.mark_failed("No chunks generated from document")
                await self._document_repository.update(document)
                return document

            # Store chunks in vector store under scope-based namespace
            namespace = document.scope.value
            await self._vector_store.upsert_chunks(
                chunks, document.id, namespace=namespace
            )

            # Mark as completed
            document.mark_completed(chunk_count=len(chunks))
            await self._document_repository.update(document)
        except Exception as e:
            # Mark as failed
            document.mark_failed(str(e))
            await self._document_repository.update(document)
            raise

        return document

    async def reprocess_document(self, document_id: str) -> Document:
        """Reprocess an existing document.

        Args:
            document_id: ID of the document to reprocess

        Returns:
            The reprocessed document
        """
        from uuid import UUID

        document = await self._document_repository.get_by_id(UUID(document_id))
        if not document:
            raise ValueError(_ERR_DOCUMENT_NOT_FOUND.format(document_id))

        # Delete existing chunks from vector store (using current scope namespace)
        await self._vector_store.delete_by_document(
            document.id, namespace=document.scope.value
        )

        # Reset status and reprocess
        document.update_status(DocumentStatus.PENDING)
        document.error_message = None
        document.chunk_count = 0
        await self._document_repository.update(document)

        return await self.process_document(document)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its vectors.

        Args:
            document_id: ID of the document to delete

        Returns:
            True if deleted successfully
        """
        from uuid import UUID

        doc_id = UUID(document_id)

        # Get document to determine namespace
        document = await self._document_repository.get_by_id(doc_id)
        namespace = document.scope.value if document else None

        # Delete from vector store first
        await self._vector_store.delete_by_document(doc_id, namespace=namespace)

        # Delete from database
        return await self._document_repository.delete(doc_id)

    def estimate_processing_time(self, document: Document) -> dict[str, object]:
        """Estimate processing time for a document.

        Returns:
            Dictionary with estimates
        """
        estimated_chunks = self._document_processor.estimate_chunks(document.content)

        # Rough estimates based on typical processing times
        chunking_time = estimated_chunks * 0.01  # 10ms per chunk
        embedding_time = estimated_chunks * 0.1  # 100ms per chunk for embedding
        upsert_time = estimated_chunks * 0.005  # 5ms per chunk for upsert

        total_time = chunking_time + embedding_time + upsert_time

        return {
            "estimated_chunks": estimated_chunks,
            "chunking_time_seconds": round(chunking_time, 2),
            "embedding_time_seconds": round(embedding_time, 2),
            "upsert_time_seconds": round(upsert_time, 2),
            "total_time_seconds": round(total_time, 2),
        }
