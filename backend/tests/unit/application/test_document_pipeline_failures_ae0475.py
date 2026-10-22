"""Document pipeline failure recording.

Feature: knowledge_ingestion_failure_ae0475.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.document_pipeline import (
    DocumentProcessingPipeline,
)
from rag_backend.domain.models import Document, DocumentChunk, DocumentStatus

_REASON = "embedding service unavailable"
_MAX_REASON_CHARS = 300


class _Repository:
    def __init__(self, document: Document) -> None:
        self.document = document
        self.updates: list[tuple[DocumentStatus, str | None]] = []

    async def get_by_id(self, document_id: object) -> Document | None:
        return self.document

    async def update(self, document: Document) -> Document:
        self.updates.append((document.status, document.error_message))
        return document


class _Processor:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    async def process(self, document: Document) -> list[DocumentChunk]:
        if self._error is not None:
            raise self._error
        return [DocumentChunk(content="chunk", document_id=document.id, index=0)]

    def estimate_chunks(self, content: str) -> int:
        return 1


class _VectorStore:
    async def upsert_chunks(
        self, chunks: list[DocumentChunk], document_id: object, namespace: str
    ) -> None:
        return None

    async def delete_by_document(self, document_id: object, namespace: str) -> None:
        return None


def _pipeline(
    document: Document, error: Exception | None = None
) -> tuple[DocumentProcessingPipeline, _Repository]:
    repository = _Repository(document)
    pipeline = DocumentProcessingPipeline(
        document_repository=repository,
        document_processor=_Processor(error),
        vector_store=_VectorStore(),
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
    assert result.error_message == f"RuntimeError: {_REASON}"
    assert result.chunk_count == 0
    assert repository.updates[-1] == (
        DocumentStatus.FAILED,
        f"RuntimeError: {_REASON}",
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
async def test_failure_reason_is_short_and_typed() -> None:
    # Scenario: The failure reason is short and names the error type
    document = _document()
    pipeline, _ = _pipeline(document, ValueError("x" * 2000))

    result = await pipeline.reprocess_document(str(document.id))

    assert result.error_message is not None
    assert result.error_message.startswith("ValueError: xxx")
    assert len(result.error_message) <= _MAX_REASON_CHARS


@pytest.mark.asyncio
async def test_ingest_processing_still_raises() -> None:
    # Scenario: An upload whose processing fails still rolls back
    document = _document()
    pipeline, repository = _pipeline(document, RuntimeError(_REASON))

    with pytest.raises(RuntimeError, match=_REASON):
        await pipeline.process_document(document)

    assert repository.updates[-1][0] == DocumentStatus.FAILED
