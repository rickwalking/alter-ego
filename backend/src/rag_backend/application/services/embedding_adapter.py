"""Embedding adapter for feedback learning loop."""

from __future__ import annotations

from rag_backend.infrastructure.external.openai_embeddings import OpenAIEmbeddingService


class EmbeddingAdapter:
    """Adapts OpenAIEmbeddingService to the feedback loop embed API."""

    def __init__(self, service: OpenAIEmbeddingService) -> None:
        self._service = service

    async def embed(self, text: str) -> list[float]:
        vectors = await self._service.embed_dense([text])
        return vectors[0]


__all__ = ["EmbeddingAdapter"]
