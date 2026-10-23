"""The owner moves a knowledge document between the personal and public scopes."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.domain.models import (
    Document,
    DocumentChunk,
    DocumentScope,
    DocumentStatus,
    UserRole,
)
from tests.integration.test_knowledge_safety_net import (
    KnowledgeEnv,
    kb_env,
)
from tests.pinecone_index_fakes import FakePineconeIndex, store_over

__all__ = ["kb_env"]

_PERSONAL = DocumentScope.PERSONAL.value
_PUBLIC = DocumentScope.PUBLIC.value


@dataclass
class _Index:
    """The stubbed vector store and processor behind the pipeline."""

    store: AsyncMock
    processor: MagicMock

    def deleted_from(self) -> list[str]:
        return [
            call.kwargs["namespace"]
            for call in self.store.delete_by_document.await_args_list
        ]

    def indexed_in(self) -> list[str]:
        return [
            call.kwargs["namespace"]
            for call in self.store.upsert_chunks.await_args_list
        ]


def _chunks(document: Document) -> list[DocumentChunk]:
    return [DocumentChunk(content="chunk", document_id=document.id, index=0)]


@pytest.fixture
def index(kb_env: KnowledgeEnv) -> Iterator[_Index]:
    container = kb_env.container
    store = AsyncMock()
    processor = MagicMock()
    processor.process = AsyncMock(side_effect=_chunks)
    processor.estimate_chunks = MagicMock(return_value=1)
    container.vector_store.override(store)
    container.document_processor.override(processor)
    yield _Index(store=store, processor=processor)
    container.document_processor.reset_override()


@pytest.fixture
def pinecone(kb_env: KnowledgeEnv, index: _Index) -> Iterator[FakePineconeIndex]:
    """The real Pinecone store over an in-memory index that holds vectors."""
    fake = FakePineconeIndex()
    kb_env.container.vector_store.override(store_over(fake))
    yield fake
    kb_env.container.vector_store.override(index.store)


def _scope_url(document_id: object) -> str:
    return f"/api/documents/{document_id}/scope"


@pytest.mark.integration
class TestChangeDocumentScope:
    async def test_personal_document_becomes_public(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: Making a personal document public re-indexes it in the public namespace"""
        document = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PUBLIC}
            )

        assert response.status_code == 200
        body = response.json()
        assert body["scope"] == _PUBLIC
        assert body["is_public"] is True
        assert body["status"] == DocumentStatus.COMPLETED.value
        assert index.deleted_from() == [_PERSONAL, _PUBLIC]
        assert index.indexed_in() == [_PUBLIC]
        async with kb_env.client_for(kb_env.owner) as client:
            stored = (await client.get(f"/api/documents/{document.id}")).json()
        assert stored["scope"] == _PUBLIC
        assert stored["is_public"] is True

    async def test_public_document_becomes_personal(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: Making a public document personal re-indexes it in the personal namespace"""
        document = await kb_env.seed_document(
            kb_env.owner.id, scope=DocumentScope.PUBLIC, is_public=True
        )
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PERSONAL}
            )

        assert response.status_code == 200
        assert response.json()["scope"] == _PERSONAL
        assert response.json()["is_public"] is False
        assert index.deleted_from() == [_PUBLIC, _PERSONAL]
        assert index.indexed_in() == [_PERSONAL]

    async def test_same_scope_changes_nothing(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: The same scope changes nothing"""
        document = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PERSONAL}
            )

        assert response.status_code == 200
        assert response.json()["scope"] == _PERSONAL
        assert response.json()["chunk_count"] == document.chunk_count
        assert index.store.delete_by_document.await_count == 0
        assert index.processor.process.await_count == 0

    @pytest.mark.parametrize(
        "scope",
        [DocumentScope.CAROUSEL.value, DocumentScope.INTERNAL.value, "everyone"],
    )
    async def test_only_personal_and_public_can_be_chosen(
        self, kb_env: KnowledgeEnv, index: _Index, scope: str
    ) -> None:
        """Scenario: Only the personal and public scopes can be chosen"""
        document = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": scope}
            )

        assert response.status_code == 400
        assert index.store.delete_by_document.await_count == 0

    async def test_someone_elses_document_is_refused(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: A document of someone else cannot be rescoped"""
        other = await kb_env.make_user(
            "kb-scope-other@integration.test", UserRole.EDITOR
        )
        document = await kb_env.seed_document(other.id)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PUBLIC}
            )

        assert response.status_code == 403
        assert index.store.delete_by_document.await_count == 0

    async def test_admin_can_rescope_any_document(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: An admin can rescope any document"""
        other = await kb_env.make_user("kb-scope-o2@integration.test", UserRole.EDITOR)
        admin = await kb_env.make_user(
            "kb-scope-admin@integration.test", UserRole.ADMIN
        )
        document = await kb_env.seed_document(other.id)
        async with kb_env.client_for(admin) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PUBLIC}
            )

        assert response.status_code == 200
        assert response.json()["scope"] == _PUBLIC
        assert response.json()["is_public"] is True

    async def test_unknown_document_is_not_found(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: An unknown document cannot be rescoped"""
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(_scope_url(uuid4()), json={"scope": _PUBLIC})

        assert response.status_code == 404

    async def test_anonymous_visitor_is_refused(
        self, kb_env: KnowledgeEnv, index: _Index
    ) -> None:
        """Scenario: An anonymous visitor cannot rescope a document"""
        document = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.anon_client() as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PUBLIC}
            )

        assert response.status_code == 401
        assert index.store.delete_by_document.await_count == 0

    @pytest.mark.parametrize("scope", [DocumentScope.CAROUSEL, DocumentScope.INTERNAL])
    async def test_system_document_is_refused(
        self, kb_env: KnowledgeEnv, index: _Index, scope: DocumentScope
    ) -> None:
        """Scenario: A system document cannot be rescoped"""
        document = await kb_env.seed_document(kb_env.owner.id, scope=scope)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(
                _scope_url(document.id), json={"scope": _PUBLIC}
            )

        assert response.status_code == 409
        assert index.store.delete_by_document.await_count == 0
        assert index.processor.process.await_count == 0
        async with kb_env.client_for(kb_env.owner) as client:
            stored = (await client.get(f"/api/documents/{document.id}")).json()
        assert stored["scope"] == scope.value


@pytest.mark.integration
class TestSharedNamespace:
    async def test_rescope_leaves_the_other_document(
        self, kb_env: KnowledgeEnv, pinecone: FakePineconeIndex
    ) -> None:
        """Scenario: Rescoping one document leaves the other documents of its namespace"""
        first = await kb_env.seed_document(kb_env.owner.id)
        second = await kb_env.seed_document(kb_env.owner.id)
        pinecone.seed(first.id, _PERSONAL)
        pinecone.seed(second.id, _PERSONAL)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.patch(_scope_url(first.id), json={"scope": _PUBLIC})

        assert response.status_code == 200
        assert pinecone.documents_in(_PERSONAL) == {second.id}
        assert pinecone.documents_in(_PUBLIC) == {first.id}

    async def test_delete_leaves_the_other_document(
        self, kb_env: KnowledgeEnv, pinecone: FakePineconeIndex
    ) -> None:
        """Scenario: Deleting one document leaves the other documents of its namespace"""
        first = await kb_env.seed_document(kb_env.owner.id)
        second = await kb_env.seed_document(kb_env.owner.id)
        pinecone.seed(first.id, _PERSONAL)
        pinecone.seed(second.id, _PERSONAL)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.delete(f"/api/documents/{first.id}")

        assert response.status_code == 204
        assert pinecone.documents_in(_PERSONAL) == {second.id}
