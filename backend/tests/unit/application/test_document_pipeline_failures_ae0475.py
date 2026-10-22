"""Document pipeline failure recording.

Feature: knowledge_ingestion_failure_ae0475.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.document_pipeline import (
    DocumentProcessingPipeline,
)
from rag_backend.domain.constants.documents import (
    FAILURE_EMBEDDING_UNAVAILABLE,
    FAILURE_EMPTY_CONTENT,
    FAILURE_PROCESSING_ERROR,
    FAILURE_VECTOR_STORE_UNAVAILABLE,
)
from rag_backend.domain.models import Document, DocumentChunk, DocumentStatus

_REASON = "embedding service unavailable"
_SECRET_LOOKING = (
    "connect to https://embed.internal.example:8443/v1 failed, "
    "api key sk-proj-AbC1***xyz rejected"
)


class _Repository:
    def __init__(
        self, document: Document, fail_on: DocumentStatus | None = None
    ) -> None:
        self.document = document
        self.fail_on = fail_on
        self.updates: list[tuple[DocumentStatus, str | None]] = []

    async def get_by_id(self, document_id: object) -> Document | None:
        return self.document

    async def update(self, document: Document) -> Document:
        self.updates.append((document.status, document.error_message))
        if document.status == self.fail_on:
            self.fail_on = None
            raise RuntimeError(_SECRET_LOOKING)
        return document


class _Processor:
    def __init__(self, error: Exception | None = None, *, empty: bool = False) -> None:
        self._error = error
        self._empty = empty

    async def process(self, document: Document) -> list[DocumentChunk]:
        if self._error is not None:
            raise self._error
        if self._empty:
            return []
        return [DocumentChunk(content="chunk", document_id=document.id, index=0)]

    def estimate_chunks(self, content: str) -> int:
        return 1


class _VectorStore:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    async def upsert_chunks(
        self, chunks: list[DocumentChunk], document_id: object, namespace: str
    ) -> None:
        if self._error is not None:
            raise self._error

    async def delete_by_document(self, document_id: object, namespace: str) -> None:
        return None


def _pipeline(
    document: Document,
    error: Exception | None = None,
    *,
    processor: _Processor | None = None,
    vector_store: _VectorStore | None = None,
    repository: _Repository | None = None,
) -> tuple[DocumentProcessingPipeline, _Repository]:
    repository = repository or _Repository(document)
    pipeline = DocumentProcessingPipeline(
        document_repository=repository,
        document_processor=processor or _Processor(error),
        vector_store=vector_store or _VectorStore(),
    )
    return pipeline, repository


def _document(status: DocumentStatus = DocumentStatus.PENDING) -> Document:
    return Document(content="Spec first.", title="Spec", status=status)


@pytest.mark.asyncio
async def test_failed_reprocess_is_recorded_not_raised() -> None:
    # Scenario: A failed reprocess is saved as failed with the reason
    document = _document()
    pipeline, repository = _pipeline(document, RuntimeError(_REASON))

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.FAILED
    assert result.error_message == FAILURE_EMBEDDING_UNAVAILABLE
    assert result.chunk_count == 0
    assert repository.updates[-1] == (
        DocumentStatus.FAILED,
        FAILURE_EMBEDDING_UNAVAILABLE,
    )


@pytest.mark.asyncio
async def test_successful_reprocess_clears_the_failure() -> None:
    # Scenario: A successful reprocess clears an earlier failure
    document = _document(DocumentStatus.FAILED)
    document.error_message = "RuntimeError: earlier"
    pipeline, _ = _pipeline(document)

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.COMPLETED
    assert result.chunk_count == 1
    assert result.error_message is None


@pytest.mark.asyncio
async def test_saved_reason_never_carries_the_error_text() -> None:
    # Scenario: The saved reason never carries the error text
    document = _document()
    pipeline, repository = _pipeline(document, ConnectionError(_SECRET_LOOKING))

    result = await pipeline.reprocess_document(str(document.id))

    assert result.error_message == FAILURE_EMBEDDING_UNAVAILABLE
    saved = [message for _, message in repository.updates if message]
    assert saved == [FAILURE_EMBEDDING_UNAVAILABLE]
    for fragment in ("embed.internal.example", "https://", "sk-proj", "8443"):
        assert all(fragment not in message for message in saved)


@pytest.mark.asyncio
async def test_vector_store_failure_is_saved_as_vector_store_unavailable() -> None:
    # Scenario: A vector store failure is saved as vector store unavailable
    document = _document()
    pipeline, _ = _pipeline(
        document, vector_store=_VectorStore(RuntimeError(_SECRET_LOOKING))
    )

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.FAILED
    assert result.error_message == FAILURE_VECTOR_STORE_UNAVAILABLE


@pytest.mark.asyncio
async def test_document_without_chunks_is_saved_as_empty_content() -> None:
    # Scenario: A document without content is saved as empty content
    document = _document()
    pipeline, _ = _pipeline(document, processor=_Processor(empty=True))

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.FAILED
    assert result.error_message == FAILURE_EMPTY_CONTENT


@pytest.mark.asyncio
async def test_other_failure_is_saved_as_processing_error() -> None:
    # Scenario: Any other failure is saved as a processing error
    document = _document()
    repository = _Repository(document, fail_on=DocumentStatus.PROCESSING)
    pipeline, _ = _pipeline(document, repository=repository)

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.FAILED
    assert result.error_message == FAILURE_PROCESSING_ERROR


@pytest.mark.asyncio
async def test_failure_after_the_upsert_is_saved_as_processing_error() -> None:
    # Scenario: Any other failure is saved as a processing error
    document = _document()
    repository = _Repository(document, fail_on=DocumentStatus.COMPLETED)
    pipeline, _ = _pipeline(document, repository=repository)

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.FAILED
    assert result.error_message == FAILURE_PROCESSING_ERROR


@pytest.mark.asyncio
async def test_failure_after_the_embedding_is_saved_as_processing_error() -> None:
    # Scenario: Any other failure is saved as a processing error
    document = _document()
    repository = _Repository(document, fail_on=DocumentStatus.FAILED)
    pipeline, _ = _pipeline(
        document, processor=_Processor(empty=True), repository=repository
    )

    result = await pipeline.reprocess_document(str(document.id))

    assert result.status == DocumentStatus.FAILED
    assert result.error_message == FAILURE_PROCESSING_ERROR


@pytest.mark.asyncio
async def test_ingest_processing_still_raises() -> None:
    # Scenario: An upload whose processing fails still rolls back
    document = _document()
    pipeline, repository = _pipeline(document, RuntimeError(_REASON))

    with pytest.raises(RuntimeError, match=_REASON):
        await pipeline.process_document(document)

    assert repository.updates[-1][0] == DocumentStatus.FAILED
