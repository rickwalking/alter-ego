"""Pinecone vector store implementation with hybrid search."""

from typing import Any
from uuid import UUID

from pinecone import Pinecone, ServerlessSpec

from rag_backend.domain.models import DocumentChunk, SearchResult
from rag_backend.infrastructure.config.settings import Settings


class PineconeVectorStore:
    """Pinecone implementation of VectorStore protocol with hybrid search support."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Pinecone(api_key=settings.pinecone_api_key)
        self._index_name = settings.pinecone_index_name
        self._index = None

    async def _get_index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            # Check if index exists
            existing_indexes = self._client.list_indexes()
            if self._index_name not in [idx.name for idx in existing_indexes]:
                # Create index with hybrid search support
                self._client.create_index(
                    name=self._index_name,
                    dimension=3072,  # text-embedding-3-large dimension
                    metric="dotproduct",  # Required for hybrid search
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self._settings.pinecone_environment,
                    ),
                )
            self._index = self._client.Index(self._index_name)
        return self._index

    async def upsert_chunks(self, chunks: list[DocumentChunk], document_id: UUID) -> None:
        """Store document chunks with their embeddings."""
        index = await self._get_index()

        vectors = []
        for chunk in chunks:
            vector_data = {
                "id": str(chunk.id),
                "values": chunk.dense_embedding,
                "metadata": {
                    "content": chunk.content,
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.index,
                    **chunk.metadata,
                },
            }

            # Add sparse values if available (for hybrid search)
            if chunk.sparse_embedding:
                vector_data["sparse_values"] = {
                    "indices": chunk.sparse_embedding.get("indices", []),
                    "values": chunk.sparse_embedding.get("values", []),
                }

            vectors.append(vector_data)

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            index.upsert(vectors=batch, namespace=str(document_id))

    async def delete_by_document(self, document_id: UUID) -> None:
        """Delete all chunks belonging to a document."""
        index = await self._get_index()

        # Delete all vectors in the document's namespace
        index.delete(delete_all=True, namespace=str(document_id))

    async def hybrid_search(
        self,
        query: str,
        dense_embedding: list[float],
        sparse_embedding: dict[str, Any],
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> list[SearchResult]:
        """Perform hybrid search combining dense and sparse vectors.

        Args:
            query: The search query (for reference)
            dense_embedding: Dense vector from embedding model
            sparse_embedding: Sparse vector with 'indices' and 'values'
            top_k: Number of results to return
            alpha: Weight for dense vs sparse (0=BM25 only, 1=semantic only)

        Returns:
            List of SearchResult objects
        """
        index = await self._get_index()

        # Build query parameters
        query_params = {
            "vector": dense_embedding,
            "top_k": top_k,
            "include_metadata": True,
            "include_values": False,
        }

        # Add sparse vector for hybrid search if alpha < 1
        if alpha < 1.0 and sparse_embedding:
            query_params["sparse_vector"] = {
                "indices": sparse_embedding.get("indices", []),
                "values": sparse_embedding.get("values", []),
            }

        # Search across all namespaces (documents)
        results = index.query(**query_params)

        search_results = []
        for i, match in enumerate(results.matches):
            search_results.append(
                SearchResult(
                    content=match.metadata.get("content", ""),
                    document_id=UUID(match.metadata.get("document_id")),
                    score=match.score,
                    chunk_id=UUID(match.id) if match.id else None,
                    metadata={
                        k: v
                        for k, v in match.metadata.items()
                        if k not in ["content", "document_id"]
                    },
                    rank=i + 1,
                )
            )

        return search_results

    async def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        index = await self._get_index()
        stats = index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness,
        }
