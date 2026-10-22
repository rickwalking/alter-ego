"""Moving a knowledge document between scopes (service + pipeline).

Gherkin: tests/features/knowledge_document_scope_ae0502.feature
"""

from __future__ import annotations

from types import TracebackType
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.document_pipeline import (
    DocumentProcessingPipeline,
)
from rag_backend.domain.constants.documents import FAILURE_EMBEDDING_UNAVAILABLE
from rag_backend.domain.models import (
    Document,
    DocumentChunk,
    DocumentScope,
    DocumentStatus,
)
from rag_backend.modules.knowledge import ChangeDocumentScopeCommand
from rag_backend.modules.knowledge.application.service import (
    KnowledgeService,
    KnowledgeServiceDeps,
)


class _UnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def __aenter__(self) -> _UnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self.commit()


class _Repository:
    def __init__(self, document: Document | None) -> None:
        self.document = document
        self.updates: list[tuple[DocumentScope, DocumentStatus]] = []

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self.document

    async def update(self, document: Document) -> Document:
        self.updates.append((document.scope, document.status))
        return document


def _document(scope: DocumentScope = DocumentScope.PERSONAL) -> Document:
    return Document(
        content="Spec first.",
        title="Spec",
        scope=scope,
        is_public=scope is DocumentScope.PUBLIC,
        status=DocumentStatus.COMPLETED,
        chunk_count=3,
    )


def _store() -> AsyncMock:
    store = AsyncMock()
    store.delete_by_document = AsyncMock(return_value=None)
    store.upsert_chunks = AsyncMock(return_value=None)
    return store


def _processor(error: Exception | None = None) -> MagicMock:
    processor = MagicMock()

    async def process(document: Document) -> list[DocumentChunk]:
        if error is not None:
            raise error
        return [DocumentChunk(content="chunk", document_id=document.id, index=0)]

    processor.process = AsyncMock(side_effect=process)
    return processor


def _service(
    repository: _Repository, pipeline: AsyncMock
) -> tuple[KnowledgeService, _UnitOfWork]:
    unit_of_work = _UnitOfWork()
    service = KnowledgeService(
        repository=repository,
        pipeline=pipeline,
        deps=KnowledgeServiceDeps(retriever=AsyncMock(), unit_of_work=unit_of_work),
    )
    return service, unit_of_work


def _command(scope: DocumentScope) -> ChangeDocumentScopeCommand:
    return ChangeDocumentScopeCommand(document_id=uuid4(), scope=scope)


@pytest.mark.asyncio
async def test_service_moves_the_document_and_commits_once() -> None:
    """Scenario: Making a personal document public re-indexes it in the public namespace"""
    moved = _document(DocumentScope.PUBLIC)
    pipeline = AsyncMock()
    pipeline.rescope_document = AsyncMock(return_value=moved)
    service, unit_of_work = _service(_Repository(_document()), pipeline)
    command = _command(DocumentScope.PUBLIC)

    view = await service.change_scope(command)

    assert view is not None
    assert view.scope == DocumentScope.PUBLIC.value
    assert view.is_public is True
    pipeline.rescope_document.assert_awaited_once_with(
        str(command.document_id), DocumentScope.PUBLIC
    )
    assert unit_of_work.commits == 1


@pytest.mark.asyncio
async def test_service_same_scope_does_not_reindex() -> None:
    """Scenario: The same scope changes nothing"""
    pipeline = AsyncMock()
    service, _ = _service(_Repository(_document()), pipeline)

    view = await service.change_scope(_command(DocumentScope.PERSONAL))

    assert view is not None
    assert view.scope == DocumentScope.PERSONAL.value
    assert view.chunk_count == 3
    pipeline.rescope_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_unknown_document_is_none() -> None:
    """Scenario: An unknown document cannot be rescoped"""
    pipeline = AsyncMock()
    service, _ = _service(_Repository(None), pipeline)

    assert await service.change_scope(_command(DocumentScope.PUBLIC)) is None
    pipeline.rescope_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_pipeline_moves_chunks_to_the_public_namespace() -> None:
    """Scenario: Making a personal document public re-indexes it in the public namespace"""
    document = _document()
    store = _store()
    repository = _Repository(document)
    pipeline = DocumentProcessingPipeline(repository, _processor(), store)

    result = await pipeline.rescope_document(str(document.id), DocumentScope.PUBLIC)

    store.delete_by_document.assert_awaited_once_with(document.id, namespace="personal")
    assert store.upsert_chunks.await_args.kwargs["namespace"] == "public"
    assert result.scope is DocumentScope.PUBLIC
    assert result.is_public is True
    assert result.status is DocumentStatus.COMPLETED
    assert result.chunk_count == 1
    assert repository.updates[0] == (DocumentScope.PUBLIC, DocumentStatus.PENDING)


@pytest.mark.asyncio
async def test_pipeline_moves_chunks_to_the_personal_namespace() -> None:
    """Scenario: Making a public document personal re-indexes it in the personal namespace"""
    document = _document(DocumentScope.PUBLIC)
    store = _store()
    pipeline = DocumentProcessingPipeline(_Repository(document), _processor(), store)

    result = await pipeline.rescope_document(str(document.id), DocumentScope.PERSONAL)

    store.delete_by_document.assert_awaited_once_with(document.id, namespace="public")
    assert store.upsert_chunks.await_args.kwargs["namespace"] == "personal"
    assert result.is_public is False


@pytest.mark.asyncio
async def test_failed_reindex_keeps_the_new_scope_and_is_saved_failed() -> None:
    """Scenario: A failed re-index after a scope change is saved as failed"""
    document = _document()
    pipeline = DocumentProcessingPipeline(
        _Repository(document), _processor(RuntimeError("down")), _store()
    )

    result = await pipeline.rescope_document(str(document.id), DocumentScope.PUBLIC)

    assert result.scope is DocumentScope.PUBLIC
    assert result.status is DocumentStatus.FAILED
    assert result.error_message == FAILURE_EMBEDDING_UNAVAILABLE


@pytest.mark.asyncio
async def test_pipeline_unknown_document_raises() -> None:
    """Scenario: An unknown document cannot be rescoped"""
    pipeline = DocumentProcessingPipeline(_Repository(None), _processor(), _store())

    with pytest.raises(ValueError, match="not found"):
        await pipeline.rescope_document(str(uuid4()), DocumentScope.PUBLIC)
