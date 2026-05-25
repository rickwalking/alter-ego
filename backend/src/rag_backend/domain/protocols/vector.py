from typing import Protocol
from uuid import UUID

from rag_backend.domain.models import DocumentChunk, RetrievalQuery, SearchResult
from rag_backend.domain.types import SparseEmbedding, StatsResponse


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
        query: str,
        dense_embedding: list[float],
        sparse_embedding: SparseEmbedding,
        top_k: int = 5,
        alpha: float = 0.5,
        namespace: str | None = None,
    ) -> list[SearchResult]: ...

    async def get_stats(self) -> StatsResponse: ...


class EmbeddingService(Protocol):
    """Protocol for text embedding generation."""

    async def embed_dense(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_sparse(self, texts: list[str]) -> list[SparseEmbedding]: ...

    def count_tokens(self, text: str) -> int: ...


class Retriever(Protocol):
    """Protocol for hybrid retrieval with RRF fusion."""

    async def retrieve(self, request: RetrievalQuery) -> list[SearchResult]: ...
