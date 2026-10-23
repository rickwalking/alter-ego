"""Retry and delete clear a document's chunks from both selectable scopes.

Runs the real routes, Unit of Work, session, pipeline and ``PineconeVectorStore``
over an in-memory index that holds vectors.
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.document_pipeline import (
    DocumentProcessingPipeline,
)
from rag_backend.domain.models import DocumentScope, DocumentStatus
from rag_backend.platform.database.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.test_knowledge_document_scope_ae0502 import (
    _Index,
    index,
    pinecone,
)
from tests.integration.test_knowledge_safety_net import KnowledgeEnv, kb_env
from tests.pinecone_index_fakes import FakePineconeIndex

__all__ = ["index", "kb_env", "pinecone"]

_PERSONAL = DocumentScope.PERSONAL.value
_PUBLIC = DocumentScope.PUBLIC.value
_SAVE_FAILED = "commit failed"
_DROP_FAILED = "pinecone down"


def _fail_first_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    original = SqlAlchemyUnitOfWork.commit
    calls = {"count": 0}

    async def commit(self: SqlAlchemyUnitOfWork) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError(_SAVE_FAILED)
        await original(self)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)


def _fail_chunk_drop(monkeypatch: pytest.MonkeyPatch) -> None:
    async def drop_chunks(
        self: DocumentProcessingPipeline, document_id: str, scope: DocumentScope
    ) -> None:
        raise ConnectionError(_DROP_FAILED)

    monkeypatch.setattr(DocumentProcessingPipeline, "drop_chunks", drop_chunks)


@pytest.mark.integration
class TestClearOtherNamespace:
    async def test_retry_after_a_failed_move_clears_the_public_namespace(
        self,
        kb_env: KnowledgeEnv,
        index: _Index,
        pinecone: FakePineconeIndex,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Scenario: Retry after a failed scope change clears the other scope's namespace"""
        document = await kb_env.seed_document(kb_env.owner.id)
        pinecone.seed(document.id, _PERSONAL)
        _fail_first_commit(monkeypatch)
        _fail_chunk_drop(monkeypatch)
        async with kb_env.client_for(kb_env.owner) as client:
            with pytest.raises(RuntimeError, match=_SAVE_FAILED):
                await client.patch(
                    f"/api/documents/{document.id}/scope", json={"scope": _PUBLIC}
                )
        monkeypatch.undo()

        assert pinecone.documents_in(_PUBLIC) == {document.id}
        async with kb_env.client_for(kb_env.owner) as client:
            failed = (await client.get(f"/api/documents/{document.id}")).json()
            retried = await client.post(f"/api/documents/{document.id}/reprocess")
            stored = (await client.get(f"/api/documents/{document.id}")).json()

        assert failed["scope"] == _PERSONAL
        assert failed["status"] == DocumentStatus.FAILED.value
        assert retried.status_code == 200
        assert pinecone.documents_in(_PUBLIC) == set()
        assert pinecone.documents_in(_PERSONAL) == {document.id}
        assert stored["status"] == DocumentStatus.COMPLETED.value
        assert stored["scope"] == _PERSONAL

    async def test_delete_clears_both_namespaces(
        self, kb_env: KnowledgeEnv, pinecone: FakePineconeIndex
    ) -> None:
        """Scenario: Deleting a document clears both selectable namespaces"""
        document = await kb_env.seed_document(kb_env.owner.id)
        other = await kb_env.seed_document(kb_env.owner.id)
        pinecone.seed(document.id, _PERSONAL)
        pinecone.seed(document.id, _PUBLIC)
        pinecone.seed(other.id, _PUBLIC)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.delete(f"/api/documents/{document.id}")

        assert response.status_code == 204
        assert pinecone.documents_in(_PERSONAL) == set()
        assert pinecone.documents_in(_PUBLIC) == {other.id}

    async def test_delete_and_retry_work_on_a_fresh_index(
        self, kb_env: KnowledgeEnv, index: _Index, pinecone: FakePineconeIndex
    ) -> None:
        """Scenario: A delete in a namespace that does not exist yet deletes nothing"""
        retried = await kb_env.seed_document(kb_env.owner.id)
        deleted = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            retry = await client.post(f"/api/documents/{retried.id}/reprocess")
            delete = await client.delete(f"/api/documents/{deleted.id}")

        assert retry.status_code == 200
        assert retry.json()["status"] == DocumentStatus.COMPLETED.value
        assert pinecone.documents_in(_PERSONAL) == {retried.id}
        assert delete.status_code == 204
