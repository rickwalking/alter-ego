"""Protocol for vector database operations with parameterized hybrid search."""

from typing import Protocol
from uuid import UUID

from rag_backend.domain.models import (
    DocumentChunk,
    HybridSearchParams,
    RetrievalQuery,
    SearchResult,
)


class EmbeddingService(Protocol):
    """Protocol for embedding service."""

    async def embed_documents(self, documents: list[str]) -> list[list[float]]: ...
    async def embed_query(self, query: str) -> list[float]: ...


class Retriever(Protocol):
    """Protocol for document retrieval."""

    async def search(
        self,
        query: RetrievalQuery,
        top_k: int = 5,
    ) -> list[SearchResult]: ...


class VectorStore(Protocol):
    """Protocol for vector database operations."""

    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        document_id: UUID,
        namespace: str | None = None,
    ) -> None: ...

    async def delete_by_document(
        self, document_id: UUID, namespace: str | None = None
    ) -> None: ...

    async def hybrid_search(
        self,
        params: HybridSearchParams,
    ) -> list[SearchResult]: ...
