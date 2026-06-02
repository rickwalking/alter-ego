"""Hybrid retriever with Reciprocal Rank Fusion (RRF)."""

from dataclasses import dataclass, field

from rag_backend.domain.models import HybridSearchParams, RetrievalQuery, SearchResult
from rag_backend.domain.protocols import EmbeddingService, VectorStore


@dataclass
class _DocScore:
    result: SearchResult
    rrf_score: float = 0.0
    ranks: list[int] = field(default_factory=list)


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
            return ["personal", "public"]
        if namespace_prefix == "personal":
            # Alter-Ego agent: personal CV/bio + public blog posts
            return ["personal", "public"]
        if namespace_prefix == "carousel":
            return ["carousel"]
        if namespace_prefix == "internal":
            return ["internal"]
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

        RRF combines multiple ranked lists by assigning scores based on rank:
        score = 1 / (k + rank) where k is a constant (typically 60)
        """
        if not results:
            return []

        # Group results by document_id to handle duplicates
        doc_scores: dict[str, _DocScore] = {}

        for rank, result in enumerate(results, start=1):
            doc_id = str(result.document_id)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = _DocScore(result=result)

            # Calculate RRF score for this rank
            rrf_score = 1.0 / (self.RRF_K + rank)
            doc_scores[doc_id].rrf_score += rrf_score
            doc_scores[doc_id].ranks.append(rank)

        # Sort by RRF score (descending)
        sorted_docs = sorted(
            doc_scores.items(), key=lambda x: x[1].rrf_score, reverse=True
        )

        # Create final results with RRF scores
        final_results = []
        for i, (_doc_id, data) in enumerate(sorted_docs[:top_k], start=1):
            result = data.result
            result.score = data.rrf_score
            result.rank = i
            final_results.append(result)

        return final_results
