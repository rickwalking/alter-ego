"""A delete in a Pinecone namespace that does not exist yet is nothing to delete.

Pinecone answers 404 (``NotFoundException``) for a delete in a namespace nothing
was ever indexed in, as on a fresh prod index. The fake index does the same.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

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


def _document(scope: DocumentScope = DocumentScope.PERSONAL) -> Document:
    return Document(
        content="Spec first.",
        title="Spec",
        scope=scope,
        status=DocumentStatus.FAILED,
        chunk_count=0,
    )


def _processor() -> MagicMock:
    processor = MagicMock()

    async def process(document: Document) -> list[DocumentChunk]:
        return [
            DocumentChunk(
                content="chunk", document_id=document.id, index=0, dense_embedding=[0.1]
            )
        ]

    processor.process = AsyncMock(side_effect=process)
    return processor


def _pipeline(
    index: FakePineconeIndex, document: Document
) -> tuple[DocumentProcessingPipeline, _Repository]:
    repository = _Repository([document])
    return DocumentProcessingPipeline(repository, _processor(), store_over(index)), (
        repository
    )


async def test_the_store_treats_a_missing_namespace_as_nothing_to_delete() -> None:
    """Scenario: A delete in a namespace that does not exist yet deletes nothing"""
    index = FakePineconeIndex()

    await store_over(index).delete_by_document(uuid4(), namespace=_PUBLIC)

    assert index.delete_calls == [_PUBLIC]


async def test_deleting_a_document_never_indexed_succeeds() -> None:
    """Scenario: A delete in a namespace that does not exist yet deletes nothing"""
    index = FakePineconeIndex()
    document = _document()
    pipeline, repository = _pipeline(index, document)

    assert await pipeline.delete_document(str(document.id)) is True

    assert repository.documents == {}
    assert index.delete_calls == [_PERSONAL, _PUBLIC]


async def test_retry_on_a_fresh_index_indexes_the_document() -> None:
    """Scenario: A delete in a namespace that does not exist yet deletes nothing"""
    index = FakePineconeIndex()
    document = _document()
    pipeline, _ = _pipeline(index, document)

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status is DocumentStatus.COMPLETED
    assert index.documents_in(_PERSONAL) == {document.id}
    assert index.delete_calls == [_PERSONAL, _PUBLIC]


async def test_rescope_into_a_namespace_that_does_not_exist_yet() -> None:
    """Scenario: A delete in a namespace that does not exist yet deletes nothing"""
    index = FakePineconeIndex()
    document = _document()
    index.seed(document.id, _PERSONAL)
    pipeline, _ = _pipeline(index, document)

    result = await pipeline.rescope_document(str(document.id), DocumentScope.PUBLIC)

    assert result.status is DocumentStatus.COMPLETED
    assert index.documents_in(_PERSONAL) == set()
    assert index.documents_in(_PUBLIC) == {document.id}


async def test_a_system_scope_document_clears_only_its_own_namespace() -> None:
    """Scenario: A system scope document clears only its own namespace"""
    index = FakePineconeIndex()
    document = _document(DocumentScope.CAROUSEL)
    pipeline, _ = _pipeline(index, document)

    await pipeline.reprocess_document(str(document.id))

    assert index.delete_calls == [DocumentScope.CAROUSEL.value]


async def test_other_errors_still_raise() -> None:
    """Scenario: A delete in a namespace that does not exist yet deletes nothing"""
    index = MagicMock()
    index.delete = MagicMock(side_effect=RuntimeError("denied"))
    store = store_over(FakePineconeIndex())
    store._index = index

    with pytest.raises(RuntimeError, match="denied"):
        await store.delete_by_document(uuid4(), namespace=_PUBLIC)
