"""Pinecone vector store implementation with hybrid search."""

from uuid import UUID

from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import NotFoundException

from rag_backend.domain.constants.retry import PINECONE_MAX_ATTEMPTS
from rag_backend.domain.models import DocumentChunk, HybridSearchParams, SearchResult
from rag_backend.domain.retry import retry_sync
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_DOCUMENT_ID_KEY = "document_id"
_EQ_OPERATOR = "$eq"


class PineconeVectorStore:
    """Pinecone implementation of VectorStore protocol with hybrid search support."""

    def __init__(self, settings: Settings) -> None:
        """Store the settings; the Pinecone client is built lazily on first index access.

        Merely resolving this provider (DI wiring, tests that stub the store) never
        requires a live ``PINECONE_API_KEY``; the client is created the first time a
        vector op runs.
        """
        self._settings = settings
        self._client: Pinecone | None = None
        self._index_name = settings.pinecone_index_name
        self._index = None

    def _get_client(self) -> Pinecone:
        if self._client is None:
            self._client = Pinecone(
                api_key=self._settings.pinecone_api_key.get_secret_value()
            )
        return self._client

    async def _get_index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            client = self._get_client()
            logger.info("pinecone_get_index_start", index_name=self._index_name)
            for attempt in retry_sync(attempts=PINECONE_MAX_ATTEMPTS):
                with attempt:
                    existing_indexes = client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            if self._index_name not in index_names:
                logger.info("pinecone_create_index", index_name=self._index_name)
                for attempt in retry_sync(attempts=PINECONE_MAX_ATTEMPTS):
                    with attempt:
                        client.create_index(
                            name=self._index_name,
                            dimension=3072,
                            metric="dotproduct",
                            spec=ServerlessSpec(
                                cloud="aws",
                                region=self._settings.pinecone_environment,
                            ),
                        )
            self._index = client.Index(self._index_name)
            logger.info("pinecone_get_index_ok", index_name=self._index_name)
        return self._index

    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        document_id: UUID,
        namespace: str | None = None,
    ) -> None:
        """Store document chunks with their embeddings.

        Args:
            chunks: Document chunks to upsert
            document_id: Parent document ID
            namespace: Pinecone namespace. If None, uses str(document_id).

        Sparse values are added when present (hybrid search); vectors are upserted in
        batches of 100.
        """
        index = await self._get_index()
        ns = namespace if namespace is not None else str(document_id)

        logger.info(
            "pinecone_upsert_start",
            document_id=str(document_id),
            namespace=ns,
            chunk_count=len(chunks),
        )

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

            if chunk.sparse_embedding:
                vector_data["sparse_values"] = {
                    "indices": chunk.sparse_embedding.get("indices", []),
                    "values": chunk.sparse_embedding.get("values", []),
                }

            vectors.append(vector_data)

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            for attempt in retry_sync(attempts=PINECONE_MAX_ATTEMPTS):
                with attempt:
                    index.upsert(vectors=batch, namespace=ns)

        logger.info(
            "pinecone_upsert_ok",
            document_id=str(document_id),
            namespace=ns,
            vector_count=len(vectors),
        )

    async def delete_by_document(
        self, document_id: UUID, namespace: str | None = None
    ) -> None:
        """Delete the chunks of one document, leaving the namespace's other documents.

        The scope namespaces are shared by every document of that scope, so the
        delete filters on the chunk's ``document_id`` metadata instead of
        clearing the namespace. Pinecone answers 404 for a namespace that does
        not exist yet (nothing was ever indexed there); that means there is
        nothing to delete, so it is logged and not raised (and not retried).

        Args:
            document_id: Parent document ID
            namespace: Pinecone namespace. If None, uses str(document_id).
        """
        index = await self._get_index()
        ns = namespace if namespace is not None else str(document_id)
        document_filter = {_DOCUMENT_ID_KEY: {_EQ_OPERATOR: str(document_id)}}

        try:
            for attempt in retry_sync(attempts=PINECONE_MAX_ATTEMPTS):
                with attempt:
                    index.delete(filter=document_filter, namespace=ns)
        except NotFoundException:
            logger.info(
                "pinecone_delete_namespace_missing",
                document_id=str(document_id),
                namespace=ns,
            )

    async def hybrid_search(
        self,
        params: HybridSearchParams,
    ) -> list[SearchResult]:
        """Perform hybrid search combining dense and sparse vectors.

        Args:
            params: Hybrid search parameters (query, embeddings, top_k, alpha, namespace)

        Returns:
            List of SearchResult objects

        The sparse vector is sent only when ``alpha < 1``.
        """
        index = await self._get_index()

        query_params: dict[str, object] = {
            "vector": params.dense_embedding,
            "top_k": params.top_k,
            "include_metadata": True,
            "include_values": False,
        }

        if params.namespace is not None:
            query_params["namespace"] = params.namespace

        if params.alpha < 1.0 and params.sparse_embedding:
            query_params["sparse_vector"] = {
                "indices": params.sparse_embedding.get("indices", []),
                "values": params.sparse_embedding.get("values", []),
            }

        for attempt in retry_sync(attempts=PINECONE_MAX_ATTEMPTS):
            with attempt:
                results = index.query(**query_params)

        match_count = len(results.matches) if results else 0
        logger.info(
            "pinecone_hybrid_search",
            query=params.query,
            namespace=params.namespace,
            top_k=params.top_k,
            alpha=params.alpha,
            match_count=match_count,
        )

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
                        if k not in {"content", "document_id"}
                    },
                    rank=i + 1,
                )
            )

        return search_results
