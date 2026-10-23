"""Deleting one document's vectors leaves the other documents of a shared namespace.

The scope namespaces (``personal``, ``public``) hold every document of that
scope, so the store, the reprocess, the rescope and the delete must remove one
document's chunks only. The index here really holds vectors.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from rag_backend.application.services.document_pipeline import (
    DocumentProcessingPipeline,
)
from rag_backend.domain.models import (
    Document,
    DocumentChunk,
    DocumentScope,
    DocumentStatus,
)
from tests.pinecone_index_fakes import FakePineconeIndex, store_over

_PERSONAL = DocumentScope.PERSONAL.value
_PUBLIC = DocumentScope.PUBLIC.value


class _Repository:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = {document.id: document for document in documents}

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self.documents.get(document_id)

    async def update(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def delete(self, document_id: UUID) -> bool:
        return self.documents.pop(document_id, None) is not None


def _completed(title: str) -> Document:
    return Document(
        content=title,
        title=title,
        scope=DocumentScope.PERSONAL,
        status=DocumentStatus.COMPLETED,
        chunk_count=1,
    )


def _processor() -> MagicMock:
    processor = MagicMock()

    async def process(document: Document) -> list[DocumentChunk]:
        return [
            DocumentChunk(
                content=document.title,
                document_id=document.id,
                index=0,
                dense_embedding=[0.1],
            )
        ]

    processor.process = AsyncMock(side_effect=process)
    return processor


def _two_personal_documents() -> tuple[FakePineconeIndex, Document, Document]:
    index = FakePineconeIndex()
    first, second = _completed("first"), _completed("second")
    index.seed(first.id, _PERSONAL)
    index.seed(second.id, _PERSONAL)
    return index, first, second


async def test_store_deletes_only_the_given_document() -> None:
    """Scenario: Deleting one document leaves the other documents of its namespace"""
    index, first, second = _two_personal_documents()

    await store_over(index).delete_by_document(first.id, namespace=_PERSONAL)

    assert index.documents_in(_PERSONAL) == {second.id}


async def test_store_without_namespace_uses_the_document_namespace() -> None:
    """Scenario: Deleting one document leaves the other documents of its namespace"""
    index, first, second = _two_personal_documents()
    index.seed(first.id, str(first.id))

    await store_over(index).delete_by_document(first.id)

    assert index.documents_in(str(first.id)) == set()
    assert index.documents_in(_PERSONAL) == {first.id, second.id}


async def test_rescope_leaves_the_other_document_in_the_old_namespace() -> None:
    """Scenario: Rescoping one document leaves the other documents of its namespace"""
    index, first, second = _two_personal_documents()
    pipeline = DocumentProcessingPipeline(
        _Repository([first, second]), _processor(), store_over(index)
    )

    await pipeline.rescope_document(str(first.id), DocumentScope.PUBLIC)

    assert index.documents_in(_PERSONAL) == {second.id}
    assert index.documents_in(_PUBLIC) == {first.id}


async def test_reprocess_leaves_the_other_document_in_the_namespace() -> None:
    """Scenario: Rescoping one document leaves the other documents of its namespace"""
    index, first, second = _two_personal_documents()
    pipeline = DocumentProcessingPipeline(
        _Repository([first, second]), _processor(), store_over(index)
    )

    await pipeline.reprocess_document(str(first.id))

    assert index.documents_in(_PERSONAL) == {first.id, second.id}


async def test_delete_document_leaves_the_other_document() -> None:
    """Scenario: Deleting one document leaves the other documents of its namespace"""
    index, first, second = _two_personal_documents()
    repository = _Repository([first, second])
    pipeline = DocumentProcessingPipeline(repository, _processor(), store_over(index))

    assert await pipeline.delete_document(str(first.id)) is True

    assert index.documents_in(_PERSONAL) == {second.id}
    assert set(repository.documents) == {second.id}
