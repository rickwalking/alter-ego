"""Unit tests for PineconeVectorStore lazy client construction.

The Pinecone client must be built lazily (on first real index access), never in
``__init__``. This lets the DI container resolve the provider — and tests that
stub the vector store — without a live ``PINECONE_API_KEY``. Production behavior
is unchanged: the client is created the first time a vector op runs.

Scenario: Given a store with no API key, when it is merely constructed, then no
Pinecone client is created (no error); when an index access occurs, then the
client is built once and cached.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.pinecone_store import PineconeVectorStore


def _store_without_key() -> PineconeVectorStore:
    settings = Settings(pinecone_api_key=SecretStr(""))
    return PineconeVectorStore(settings=settings)


def test_construction_does_not_build_client() -> None:
    """Constructing the store never instantiates the Pinecone client."""
    with patch(
        "rag_backend.infrastructure.external.pinecone_store.Pinecone"
    ) as pinecone_cls:
        store = _store_without_key()
        pinecone_cls.assert_not_called()
        assert store._client is None


def test_get_client_builds_and_caches_once() -> None:
    """_get_client builds the client on first call and caches it thereafter."""
    with patch(
        "rag_backend.infrastructure.external.pinecone_store.Pinecone"
    ) as pinecone_cls:
        sentinel = MagicMock()
        pinecone_cls.return_value = sentinel
        store = _store_without_key()

        first = store._get_client()
        second = store._get_client()

        assert first is sentinel
        assert second is sentinel
        pinecone_cls.assert_called_once()
