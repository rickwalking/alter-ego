"""Hybrid retriever with Reciprocal Rank Fusion (RRF)."""

from rag_backend.domain.constants.namespaces import (
    DEFAULT_KB_NAMESPACES,
    NAMESPACE_CAROUSEL,
    NAMESPACE_INTERNAL,
    NAMESPACE_PERSONAL,
)
from rag_backend.domain.models import HybridSearchParams, RetrievalQuery, SearchResult
from rag_backend.domain.protocols import EmbeddingService, VectorStore


class HybridRetrieverWithRRF:
    """Hybrid retriever implementing Reciprocal Rank Fusion.

    This retriever combines dense (semantic) and sparse (BM25) search results
    using RRF to provide the best of both approaches.

    RRF Formula: score = Σ(1 / (k + rank)) for each result
    where k is a constant (typically 60)
    """

    RRF_K = 60  # RRF constant
    _DOCUMENT_ID_KEY = "document_id"

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        default_alpha: float = 0.5,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._default_alpha = default_alpha

    async def retrieve(self, request: RetrievalQuery) -> list[SearchResult]:
        """Retrieve relevant chunks using hybrid search with optional filters."""
        expand_factor = 3 if request.filters else 2
        dense_embeddings = await self._embedding_service.embed_dense([request.query])
        sparse_embeddings = await self._embedding_service.embed_sparse([request.query])

        # Determine which namespace(s) to search
        namespaces = self._resolve_namespaces(request.namespace_prefix)

        all_results: list[SearchResult] = []
        for ns in namespaces:
            params = HybridSearchParams(
                query=request.query,
                dense_embedding=dense_embeddings[0],
                sparse_embedding=sparse_embeddings[0],
                top_k=request.top_k * expand_factor,
                alpha=request.alpha,
                namespace=ns,
            )
            raw = await self._vector_store.hybrid_search(params)
            all_results.extend(raw)

        ranked = self._apply_rrf(all_results, request.top_k * expand_factor)
        if not request.filters:
            return ranked[: request.top_k]
        return self._apply_filters(ranked, request.filters, request.top_k)

    def _resolve_namespaces(self, namespace_prefix: str | None) -> list[str]:
        """Resolve a namespace prefix into concrete Pinecone namespace names.

        The Alter-Ego agent searches both ``personal`` and ``public``
        namespaces so visitors can ask about Pedro's career *and* read
        published blog posts.  The Carousel agent does not search any
        of these namespaces — it uses its own data sources.
        """
        if namespace_prefix is None:
            # Default: search all knowledge-base scopes
            return DEFAULT_KB_NAMESPACES
        if namespace_prefix == NAMESPACE_PERSONAL:
            # Alter-Ego agent: personal CV/bio + public blog posts
            return DEFAULT_KB_NAMESPACES
        if namespace_prefix == NAMESPACE_CAROUSEL:
            return [NAMESPACE_CAROUSEL]
        if namespace_prefix == NAMESPACE_INTERNAL:
            return [NAMESPACE_INTERNAL]
        # Exact namespace match for any other value
        return [namespace_prefix]

    def _apply_filters(
        self,
        results: list[SearchResult],
        filters: dict[str, str | int | float | bool],
        top_k: int,
    ) -> list[SearchResult]:
        """Return the first `top_k` results where every filter matches."""
        matched: list[SearchResult] = []
        for result in results:
            if self._matches_filters(result, filters):
                matched.append(result)
                if len(matched) >= top_k:
                    break
        return matched

    def _matches_filters(
        self,
        result: SearchResult,
        filters: dict[str, str | int | float | bool],
    ) -> bool:
        """Apply each filter key against the right SearchResult field."""
        for key, value in filters.items():
            if key == self._DOCUMENT_ID_KEY:
                if str(result.document_id) != str(value):
                    return False
            elif result.metadata.get(key) != value:
                return False
        return True

    def _apply_rrf(self, results: list[SearchResult], top_k: int) -> list[SearchResult]:
        """Apply Reciprocal Rank Fusion to search results.

        RRF combines results from multiple namespaces by assigning
        scores based on rank: score = 1 / (k + rank) where k = 60.

        Duplicate chunk_ids are removed (same chunk from multiple
        namespaces), but multiple chunks from the same document are
        preserved so the LLM has richer context.
        """
        if not results:
            return []

        # Deduplicate by chunk_id to remove cross-namespace duplicates
        seen_chunks: set[str] = set()
        unique_results: list[SearchResult] = []
        for result in results:
            chunk_key = str(result.chunk_id) if result.chunk_id else str(id(result))
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                unique_results.append(result)

        if not unique_results:
            return []

        # Calculate RRF score for each individual chunk
        chunk_scores: list[tuple[SearchResult, float]] = []
        for rank, result in enumerate(unique_results, start=1):
            rrf_score = 1.0 / (self.RRF_K + rank)
            chunk_scores.append((result, rrf_score))

        # Sort by RRF score (descending)
        chunk_scores.sort(key=lambda x: x[1], reverse=True)

        # Assign final scores and ranks
        final_results = []
        for i, (result, rrf_score) in enumerate(chunk_scores[:top_k], start=1):
            result.score = rrf_score
            result.rank = i
            final_results.append(result)

        return final_results
