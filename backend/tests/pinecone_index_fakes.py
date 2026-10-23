"""An in-memory stand-in for a Pinecone index that really holds vectors per namespace.

It accepts the ``upsert``, ``delete`` and ``query`` calls ``PineconeVectorStore``
makes and applies them to its namespaces, so a test can assert which documents'
vectors are left after a delete, and which chunks a search can reach, not only
which namespace a call named.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pinecone.exceptions import NotFoundException
from pydantic import SecretStr

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.pinecone_store import PineconeVectorStore

_DOCUMENT_ID = "document_id"
_EQ = "$eq"
_DELETE_ALL = "delete_all"
_IDS = "ids"
_FILTER = "filter"
_ERR_NO_SELECTOR = "delete needs ids, a filter or delete_all"
_NAMESPACE_NOT_FOUND = "Namespace not found"

Vector = dict[str, object]
MetadataFilter = Mapping[str, Mapping[str, str] | str]


def _matches(metadata: Mapping[str, object], metadata_filter: MetadataFilter) -> bool:
    for key, condition in metadata_filter.items():
        expected = condition[_EQ] if isinstance(condition, Mapping) else condition
        if metadata.get(key) != expected:
            return False
    return True


@dataclass(frozen=True)
class FakeMatch:
    """One query match, shaped like a Pinecone match."""

    id: str
    score: float
    metadata: dict[str, object]


@dataclass(frozen=True)
class FakeQueryResponse:
    """A query answer, shaped like a Pinecone query response."""

    matches: list[FakeMatch] = field(default_factory=list)


class FakePineconeIndex:
    """Vectors kept by namespace, then by vector id.

    Like Pinecone, a delete in a namespace that does not exist yet (nothing was
    ever upserted there) raises ``NotFoundException`` (HTTP 404).
    """

    def __init__(self) -> None:
        self.namespaces: dict[str, dict[str, Vector]] = {}
        self.delete_calls: list[str] = []

    def upsert(self, vectors: list[Vector], namespace: str) -> None:
        stored = self.namespaces.setdefault(namespace, {})
        for vector in vectors:
            stored[str(vector["id"])] = vector

    def delete(self, *, namespace: str, **selector: object) -> None:
        """Apply a Pinecone delete: ``delete_all``, ``ids`` or a metadata ``filter``."""
        self.delete_calls.append(namespace)
        if namespace not in self.namespaces:
            raise NotFoundException(status=404, reason=_NAMESPACE_NOT_FOUND)
        stored = self.namespaces[namespace]
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

    def query(self, *, namespace: str = "", **_params: object) -> FakeQueryResponse:
        """Every vector of ``namespace``, in insertion order, as matches."""
        stored = self.namespaces.get(namespace, {})
        return FakeQueryResponse(
            matches=[
                FakeMatch(id=vector_id, score=1.0, metadata=dict(vector["metadata"]))
                for vector_id, vector in stored.items()
                if isinstance(vector["metadata"], Mapping)
            ]
        )

    def seed_chunk(self, document_id: UUID, namespace: str, content: str) -> UUID:
        """Index one searchable chunk of ``document_id`` in ``namespace``."""
        chunk_id = uuid4()
        self.upsert(
            [
                {
                    "id": str(chunk_id),
                    "values": [0.0],
                    "metadata": {_DOCUMENT_ID: str(document_id), "content": content},
                }
            ],
            namespace=namespace,
        )
        return chunk_id

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
