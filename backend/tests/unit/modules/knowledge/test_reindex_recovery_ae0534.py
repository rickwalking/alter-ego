"""A rolled-back scope change or reprocess leaves the document failed and retryable."""

from __future__ import annotations

from types import TracebackType
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.domain.constants.documents import FAILURE_PROCESSING_ERROR
from rag_backend.domain.models import Document, DocumentScope, DocumentStatus
from rag_backend.modules.knowledge import (
    ChangeDocumentScopeCommand,
    ReprocessDocumentCommand,
    SystemScopeError,
)
from rag_backend.modules.knowledge.application.service import (
    KnowledgeService,
    KnowledgeServiceDeps,
)

_SAVE_FAILED = "db down"


class _UnitOfWork:
    """Fails the first ``failing_commits`` commits; counts rollbacks and commits."""

    def __init__(self, failing_commits: int = 0) -> None:
        self.failing_commits = failing_commits
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        if self.failing_commits > 0:
            self.failing_commits -= 1
            raise RuntimeError(_SAVE_FAILED)
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def __aenter__(self) -> _UnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        await self.commit()


class _Repository:
    def __init__(self, document: Document | None, update_error: bool = False) -> None:
        self.document = document
        self.update_error = update_error
        self.saved: list[tuple[DocumentStatus, str | None, int]] = []
        self.events: list[str] = []

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self.document

    async def get_by_id_for_update(self, document_id: UUID) -> Document | None:
        self.events.append("lock")
        return self.document

    async def update(self, document: Document) -> Document:
        if self.update_error:
            raise RuntimeError("update failed")
        self.saved.append((
            document.status,
            document.error_message,
            document.chunk_count,
        ))
        return document


def _document(scope: DocumentScope = DocumentScope.PERSONAL) -> Document:
    return Document(
        content="Spec first.",
        title="Spec",
        scope=scope,
        status=DocumentStatus.COMPLETED,
        chunk_count=3,
    )


def _pipeline(moved: Document) -> AsyncMock:
    pipeline = AsyncMock()
    pipeline.rescope_document = AsyncMock(return_value=moved)
    pipeline.reprocess_document = AsyncMock(return_value=moved)
    return pipeline


def _service(
    repository: _Repository, pipeline: AsyncMock, unit_of_work: _UnitOfWork
) -> KnowledgeService:
    return KnowledgeService(
        repository=repository,
        pipeline=pipeline,
        deps=KnowledgeServiceDeps(retriever=AsyncMock(), unit_of_work=unit_of_work),
    )


_FAILED_SAVE = (DocumentStatus.FAILED, FAILURE_PROCESSING_ERROR, 0)


async def test_failed_save_after_rescope_marks_the_document_failed() -> None:
    """Scenario: A failed save after a scope change marks the document failed"""
    repository = _Repository(_document())
    pipeline = _pipeline(_document(DocumentScope.PUBLIC))
    unit_of_work = _UnitOfWork(failing_commits=1)
    command = ChangeDocumentScopeCommand(
        document_id=uuid4(), scope=DocumentScope.PUBLIC
    )

    with pytest.raises(RuntimeError, match=_SAVE_FAILED):
        await _service(repository, pipeline, unit_of_work).change_scope(command)

    pipeline.drop_chunks.assert_awaited_once_with(
        str(command.document_id), DocumentScope.PUBLIC
    )
    assert repository.saved == [_FAILED_SAVE]
    assert unit_of_work.commits == 1
    assert unit_of_work.rollbacks >= 1


async def test_failed_save_after_reprocess_marks_the_document_failed() -> None:
    """Scenario: A failed save after a reprocess marks the document failed"""
    repository = _Repository(_document())
    pipeline = _pipeline(_document())
    unit_of_work = _UnitOfWork(failing_commits=1)

    with pytest.raises(RuntimeError, match=_SAVE_FAILED):
        await _service(repository, pipeline, unit_of_work).reprocess(
            ReprocessDocumentCommand(document_id=uuid4())
        )

    assert repository.saved == [_FAILED_SAVE]
    assert unit_of_work.commits == 1
    pipeline.drop_chunks.assert_not_awaited()


async def test_reprocess_of_a_vanished_document_marks_nothing() -> None:
    """Scenario: A failed save after a reprocess marks the document failed"""
    repository = _Repository(None)
    pipeline = _pipeline(_document())
    pipeline.reprocess_document = AsyncMock(side_effect=ValueError("not found"))

    with pytest.raises(ValueError, match="not found"):
        await _service(repository, pipeline, _UnitOfWork()).reprocess(
            ReprocessDocumentCommand(document_id=uuid4())
        )

    assert repository.saved == []


async def test_failing_chunk_drop_keeps_the_original_error() -> None:
    """Scenario: A failing cleanup never hides the original error"""
    repository = _Repository(_document())
    pipeline = _pipeline(_document(DocumentScope.PUBLIC))
    pipeline.drop_chunks = AsyncMock(side_effect=ConnectionError("pinecone down"))
    command = ChangeDocumentScopeCommand(
        document_id=uuid4(), scope=DocumentScope.PUBLIC
    )

    with capture_logs() as logs, pytest.raises(RuntimeError, match=_SAVE_FAILED):
        await _service(
            repository, pipeline, _UnitOfWork(failing_commits=1)
        ).change_scope(command)

    events = [log["event"] for log in logs]
    assert "knowledge_rescope_drop_chunks_failed" in events
    assert repository.saved == [_FAILED_SAVE]


async def test_failing_mark_failed_keeps_the_original_error() -> None:
    """Scenario: A failing cleanup never hides the original error"""
    repository = _Repository(_document(), update_error=True)
    pipeline = _pipeline(_document(DocumentScope.PUBLIC))
    command = ChangeDocumentScopeCommand(
        document_id=uuid4(), scope=DocumentScope.PUBLIC
    )

    with capture_logs() as logs, pytest.raises(RuntimeError, match=_SAVE_FAILED):
        await _service(
            repository, pipeline, _UnitOfWork(failing_commits=1)
        ).change_scope(command)

    assert "knowledge_reindex_mark_failed_failed" in [log["event"] for log in logs]
    pipeline.drop_chunks.assert_awaited_once()


async def test_system_scope_is_refused_under_the_lock() -> None:
    """Scenario: The system scope check runs under the row lock"""
    repository = _Repository(_document(DocumentScope.CAROUSEL))
    pipeline = _pipeline(_document(DocumentScope.PUBLIC))
    command = ChangeDocumentScopeCommand(
        document_id=uuid4(), scope=DocumentScope.PUBLIC
    )

    with pytest.raises(SystemScopeError) as refused:
        await _service(repository, pipeline, _UnitOfWork()).change_scope(command)

    assert refused.value.scope is DocumentScope.CAROUSEL
    assert repository.events == ["lock"]
    pipeline.rescope_document.assert_not_awaited()
    pipeline.drop_chunks.assert_not_awaited()
    assert repository.saved == []
