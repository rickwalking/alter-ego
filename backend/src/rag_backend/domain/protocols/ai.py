from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from rag_backend.domain.models import Document, DocumentChunk, SearchResult
from rag_backend.domain.types import ChatEvent


class LLMService(Protocol):
    """Protocol for LLM interactions."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str: ...

    def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response.

        Implementations are async generators (use `yield`). The method is
        declared with plain `def` rather than `async def` so mypy matches the
        async-generator return type (`AsyncIterator[str]`) rather than
        `Coroutine[..., AsyncIterator[str]]`.
        """
        ...


class DocumentProcessor(Protocol):
    """Protocol for document chunking and processing."""

    async def process(self, document: Document) -> list[DocumentChunk]: ...

    def estimate_chunks(self, content: str) -> int: ...


class Agent(Protocol):
    """Protocol for the RAG agent."""

    async def chat(
        self, message: str, conversation_id: UUID, *, stream: bool = True
    ) -> AsyncIterator[ChatEvent]: ...

    async def search_documents(self, query: str, top_k: int = 5) -> list[SearchResult]: ...
