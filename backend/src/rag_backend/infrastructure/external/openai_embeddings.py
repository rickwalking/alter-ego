"""OpenAI embedding service implementation."""

from typing import Any

import tiktoken
from langchain_openai import OpenAIEmbeddings

from rag_backend.domain.protocols import EmbeddingService
from rag_backend.infrastructure.config.settings import Settings


class OpenAIEmbeddingService:
    """OpenAI implementation of EmbeddingService protocol."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=3072,  # text-embedding-3-large
        )
        # Tokenizer for counting tokens
        self._tokenizer = tiktoken.encoding_for_model("gpt-4")

    async def embed_dense(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embeddings for texts using OpenAI."""
        return await self._embeddings.aembed_documents(texts)

    async def embed_sparse(self, texts: list[str]) -> list[dict[str, Any]]:
        """Generate sparse (BM25-like) embeddings for texts.

        For production, you would use Pinecone's BM25 encoder or
        a proper sparse embedding model. This is a simplified version
        that creates term frequency vectors.
        """
        sparse_embeddings = []

        for text in texts:
            # Tokenize and create term frequency
            tokens = text.lower().split()
            term_freq = {}

            for token in tokens:
                # Simple token cleaning
                token = token.strip(".,!?;:()[]{}\"'")
                if token and len(token) > 2:  # Skip short tokens
                    term_freq[token] = term_freq.get(token, 0) + 1

            # Get top terms (limited to reasonable number for Pinecone)
            top_terms = sorted(term_freq.items(), key=lambda x: x[1], reverse=True)[
                :256
            ]  # Pinecone sparse vector limit

            indices = list(range(len(top_terms)))
            values = [freq for _, freq in top_terms]

            sparse_embeddings.append(
                {
                    "indices": indices,
                    "values": values,
                    "terms": [term for term, _ in top_terms],  # Keep for debugging
                }
            )

        return sparse_embeddings

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self._tokenizer.encode(text))
