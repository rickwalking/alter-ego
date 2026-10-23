"""An in-memory stand-in for a Pinecone index that really holds vectors per namespace.

It accepts the ``upsert`` and ``delete`` calls ``PineconeVectorStore`` makes and
applies them to its namespaces, so a test can assert which documents' vectors
are left after a delete, not only which namespace a call named.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pydantic import SecretStr

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.pinecone_store import PineconeVectorStore

_DOCUMENT_ID = "document_id"
_EQ = "$eq"
_DELETE_ALL = "delete_all"
_IDS = "ids"
_FILTER = "filter"
_ERR_NO_SELECTOR = "delete needs ids, a filter or delete_all"

Vector = dict[str, object]
MetadataFilter = Mapping[str, Mapping[str, str] | str]


def _matches(metadata: Mapping[str, object], metadata_filter: MetadataFilter) -> bool:
    for key, condition in metadata_filter.items():
        expected = condition[_EQ] if isinstance(condition, Mapping) else condition
        if metadata.get(key) != expected:
            return False
    return True


class FakePineconeIndex:
    """Vectors kept by namespace, then by vector id."""

    def __init__(self) -> None:
        self.namespaces: dict[str, dict[str, Vector]] = {}

    def upsert(self, vectors: list[Vector], namespace: str) -> None:
        stored = self.namespaces.setdefault(namespace, {})
        for vector in vectors:
            stored[str(vector["id"])] = vector

    def delete(self, *, namespace: str, **selector: object) -> None:
        """Apply a Pinecone delete: ``delete_all``, ``ids`` or a metadata ``filter``."""
        stored = self.namespaces.setdefault(namespace, {})
        if selector.get(_DELETE_ALL):
            stored.clear()
            return
        ids = selector.get(_IDS)
        if isinstance(ids, list):
            for vector_id in ids:
                stored.pop(str(vector_id), None)
            return
        metadata_filter = selector.get(_FILTER)
        if not isinstance(metadata_filter, Mapping):
            raise TypeError(_ERR_NO_SELECTOR)
        for vector_id, vector in list(stored.items()):
            metadata = vector["metadata"]
            if isinstance(metadata, Mapping) and _matches(metadata, metadata_filter):
                del stored[vector_id]

    def documents_in(self, namespace: str) -> set[UUID]:
        """The ids of the documents that still have a vector in ``namespace``."""
        found: set[UUID] = set()
        for vector in self.namespaces.get(namespace, {}).values():
            metadata = vector["metadata"]
            if isinstance(metadata, Mapping):
                found.add(UUID(str(metadata[_DOCUMENT_ID])))
        return found

    def seed(self, document_id: UUID, namespace: str) -> None:
        """Index one chunk of ``document_id`` in ``namespace``."""
        self.upsert(
            [
                {
                    "id": f"{document_id}-seed",
                    "values": [0.0],
                    "metadata": {_DOCUMENT_ID: str(document_id), "content": "seed"},
                }
            ],
            namespace=namespace,
        )


def store_over(index: FakePineconeIndex) -> PineconeVectorStore:
    """A real ``PineconeVectorStore`` whose index is ``index`` (no client, no key)."""
    store = PineconeVectorStore(Settings(pinecone_api_key=SecretStr("")))
    store._index = index
    return store
