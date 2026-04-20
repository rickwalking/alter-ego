"""Hybrid retriever with Reciprocal Rank Fusion (RRF)."""

from typing import Any

from rag_backend.domain.models import SearchResult
from rag_backend.domain.protocols import EmbeddingService, VectorStore


class HybridRetrieverWithRRF:
    """Hybrid retriever implementing Reciprocal Rank Fusion.

    This retriever combines dense (semantic) and sparse (BM25) search results
    using RRF to provide the best of both approaches.

    RRF Formula: score = Σ(1 / (k + rank)) for each result
    where k is a constant (typically 60)
    """

    RRF_K = 60  # RRF constant

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        default_alpha: float = 0.5,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._default_alpha = default_alpha

    async def retrieve(
        self, query: str, top_k: int = 5, alpha: float = 0.5
    ) -> list[SearchResult]:
        """Retrieve relevant chunks using hybrid search.

        Args:
            query: The search query
            top_k: Number of results to return
            alpha: Balance between dense (1.0) and sparse (0.0) search

        Returns:
            List of SearchResult objects
        """
        # Generate embeddings for the query
        dense_embeddings = await self._embedding_service.embed_dense([query])
        sparse_embeddings = await self._embedding_service.embed_sparse([query])

        # Get results from hybrid search
        results = await self._vector_store.hybrid_search(
            query=query,
            dense_embedding=dense_embeddings[0],
            sparse_embedding=sparse_embeddings[0],
            top_k=top_k * 2,  # Get more results for better fusion
            alpha=alpha,
        )

        # Apply RRF scoring
        return self._apply_rrf(results, top_k)

    async def retrieve_with_filters(
        self, query: str, filters: dict[str, Any], top_k: int = 5, alpha: float = 0.5
    ) -> list[SearchResult]:
        """Retrieve with metadata filters.

        Note: This is a simplified implementation. Full filter support
        would require passing filters to the vector store query.
        """
        # Get all results first
        results = await self.retrieve(query, top_k=top_k * 3, alpha=alpha)

        # Apply filters
        filtered_results = []
        for result in results:
            match = True
            for key, value in filters.items():
                if key == "document_id":
                    # Handle document ID filtering
                    if str(result.document_id) != str(value):
                        match = False
                        break
                elif result.metadata.get(key) != value:
                    match = False
                    break

            if match:
                filtered_results.append(result)

            if len(filtered_results) >= top_k:
                break

        return filtered_results[:top_k]

    def _apply_rrf(self, results: list[SearchResult], top_k: int) -> list[SearchResult]:
        """Apply Reciprocal Rank Fusion to search results.

        RRF combines multiple ranked lists by assigning scores based on rank:
        score = 1 / (k + rank) where k is a constant (typically 60)
        """
        if not results:
            return []

        # Group results by document_id to handle duplicates
        doc_scores: dict[str, dict[str, Any]] = {}

        for rank, result in enumerate(results, start=1):
            doc_id = str(result.document_id)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"result": result, "rrf_score": 0.0, "ranks": []}

            # Calculate RRF score for this rank
            rrf_score = 1.0 / (self.RRF_K + rank)
            doc_scores[doc_id]["rrf_score"] += rrf_score
            doc_scores[doc_id]["ranks"].append(rank)

        # Sort by RRF score (descending)
        sorted_docs = sorted(
            doc_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True
        )

        # Create final results with RRF scores
        final_results = []
        for i, (doc_id, data) in enumerate(sorted_docs[:top_k], start=1):
            result = data["result"]
            result.score = data["rrf_score"]
            result.rank = i
            final_results.append(result)

        return final_results
