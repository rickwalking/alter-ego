"""Unit tests: knowledge writes commit once / roll back with no partial writes.

These cover the AE-0091 acceptance criteria at the application-service layer:
the ``KnowledgeService`` write use cases run under the request-scoped Unit of
Work, which is the single commit owner. On success the UoW commits exactly once;
on failure it rolls back and no partial document/chunks remain persisted.

The fakes model the transaction boundary explicitly: the repository "flushes"
into a staging buffer, and only a UoW ``commit`` promotes staged rows to the
persisted store. A rollback drops the staging buffer, so asserting the persisted
store is empty proves "no partial writes".

References: tests/features/knowledge_unit_of_work.feature.
"""

from __future__ import annotations

from types import TracebackType

import pytest

from rag_backend.modules.knowledge.application.service import (
    KnowledgeService,
    KnowledgeServiceDeps,
)
from rag_backend.modules.knowledge.domain.commands import (
    CreateDocumentCommand,
    DeleteDocumentCommand,
    IngestDocumentCommand,
)
from rag_backend.modules.knowledge.domain.models import (
    KnowledgeDocument,
    RetrievalQuery,
    SearchResult,
)

_EMBED_FAILED = "embedding failed"
_VECTOR_DELETE_FAILED = "vector delete failed"
_TITLE = "Spec-Driven Development"
_CONTENT = "Write the spec before the code."


class _SpyUnitOfWork:
    """UnitOfWork double that records commit/rollback and drives the store.

    Acts as the single commit owner: ``commit`` promotes the repository's
    staged rows to the persisted store; ``rollback`` discards them.
    """

    def __init__(self, repository: _FakeRepository) -> None:
        self._repository = repository
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1
        self._repository.flush_to_store()

    async def rollback(self) -> None:
        self.rollbacks += 1
        self._repository.discard_staged()

    async def __aenter__(self) -> _SpyUnitOfWork:
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


class _FakeRepository:
    """Repository double that flushes into a staging buffer (no commit)."""

    def __init__(self) -> None:
        self.persisted: list[KnowledgeDocument] = []
        self._staged: list[KnowledgeDocument] = []

    async def create(self, document: KnowledgeDocument) -> KnowledgeDocument:
        # Flush only — staged, not yet persisted (mirrors session.flush()).
        self._staged.append(document)
        return document

    def flush_to_store(self) -> None:
        self.persisted.extend(self._staged)
        self._staged = []

    def discard_staged(self) -> None:
        self._staged = []


class _FakePipeline:
    """Pipeline double; can be told to fail at the embedding step."""

    def __init__(self, fail_process: bool = False, fail_delete: bool = False) -> None:
        self._fail_process = fail_process
        self._fail_delete = fail_delete
        self.delete_calls = 0

    async def process_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        if self._fail_process:
            raise RuntimeError(_EMBED_FAILED)
        return document

    async def reprocess_document(self, document_id: str) -> KnowledgeDocument:
        return KnowledgeDocument(title=_TITLE, content=_CONTENT)

    async def delete_document(self, document_id: str) -> bool:
        self.delete_calls += 1
        if self._fail_delete:
            raise RuntimeError(_VECTOR_DELETE_FAILED)
        return True

    def estimate_processing_time(
        self, document: KnowledgeDocument
    ) -> dict[str, object]:
        return {"estimated_chunks": 0, "total_time_seconds": 0.0}


class _FakeRetriever:
    async def retrieve(self, request: RetrievalQuery) -> list[SearchResult]:
        return []


def _build_service(
    repository: _FakeRepository,
    pipeline: _FakePipeline,
    uow: _SpyUnitOfWork,
) -> KnowledgeService:
    return KnowledgeService(
        repository=repository,
        pipeline=pipeline,
        deps=KnowledgeServiceDeps(retriever=_FakeRetriever(), unit_of_work=uow),
    )


class TestCreateCommitsOnce:
    """A successful create commits exactly once and persists the document."""

    @pytest.mark.asyncio
    async def test_create_commits_once_and_persists(self) -> None:
        # Scenario: a successful create commits exactly once
        repo = _FakeRepository()
        uow = _SpyUnitOfWork(repo)
        service = _build_service(repo, _FakePipeline(), uow)

        view = await service.create(
            CreateDocumentCommand(title=_TITLE, content=_CONTENT)
        )

        assert view.title == _TITLE
        assert uow.commits == 1
        assert uow.rollbacks == 0
        assert len(repo.persisted) == 1


class TestIngestTransaction:
    """Ingest commits once on success, rolls back with no partial writes."""

    @pytest.mark.asyncio
    async def test_ingest_commits_once_on_success(self) -> None:
        # Scenario: a successful ingest commits exactly once at the boundary
        repo = _FakeRepository()
        uow = _SpyUnitOfWork(repo)
        service = _build_service(repo, _FakePipeline(), uow)

        await service.ingest(IngestDocumentCommand(title=_TITLE, content=_CONTENT))

        assert uow.commits == 1
        assert uow.rollbacks == 0
        assert len(repo.persisted) == 1

    @pytest.mark.asyncio
    async def test_failed_ingest_rolls_back_with_no_partial_writes(self) -> None:
        # Scenario: failed ingest rolls back -> no partial document/chunks
        repo = _FakeRepository()
        uow = _SpyUnitOfWork(repo)
        service = _build_service(repo, _FakePipeline(fail_process=True), uow)

        with pytest.raises(RuntimeError, match=_EMBED_FAILED):
            await service.ingest(IngestDocumentCommand(title=_TITLE, content=_CONTENT))

        assert uow.rollbacks == 1
        assert uow.commits == 0
        assert repo.persisted == []  # no partial writes


class TestDeleteTransaction:
    """Delete commits once on success, rolls back on failure."""

    @pytest.mark.asyncio
    async def test_delete_commits_once_on_success(self) -> None:
        repo = _FakeRepository()
        uow = _SpyUnitOfWork(repo)
        service = _build_service(repo, _FakePipeline(), uow)

        deleted = await service.delete(
            DeleteDocumentCommand(
                document_id=KnowledgeDocument(title=_TITLE, content=_CONTENT).id
            )
        )

        assert deleted is True
        assert uow.commits == 1
        assert uow.rollbacks == 0

    @pytest.mark.asyncio
    async def test_failed_delete_rolls_back(self) -> None:
        # Scenario: a failed delete rolls back with no partial writes
        repo = _FakeRepository()
        uow = _SpyUnitOfWork(repo)
        service = _build_service(repo, _FakePipeline(fail_delete=True), uow)

        with pytest.raises(RuntimeError, match=_VECTOR_DELETE_FAILED):
            await service.delete(
                DeleteDocumentCommand(
                    document_id=KnowledgeDocument(title=_TITLE, content=_CONTENT).id
                )
            )

        assert uow.rollbacks == 1
        assert uow.commits == 0
