"""Unit tests for PostgreSQL repositories."""

from uuid import uuid4

import pytest

from rag_backend.domain.models import Document, DocumentScope, DocumentStatus


@pytest.mark.unit
class TestPostgresDocumentRepository:
    """Tests for PostgresDocumentRepository."""

    async def test_create_document(self, document_repository, sample_document):
        """Should create a document in the database."""
        created = await document_repository.create(sample_document)

        assert created.id is not None
        assert created.title == sample_document.title
        assert created.content == sample_document.content
        assert created.status == DocumentStatus.PENDING

    async def test_get_by_id_existing(self, document_repository, sample_document):
        """Should retrieve existing document by ID."""
        created = await document_repository.create(sample_document)

        retrieved = await document_repository.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    async def test_get_by_id_nonexistent(self, document_repository):
        """Should return None for non-existent document ID."""
        retrieved = await document_repository.get_by_id(uuid4())

        assert retrieved is None

    async def test_get_all_empty(self, document_repository):
        """Should return empty list when no documents exist."""
        documents = await document_repository.get_all()

        assert documents == []

    async def test_get_all_with_documents(self, document_repository, sample_documents):
        """Should return all created documents."""
        for doc in sample_documents:
            await document_repository.create(doc)

        documents = await document_repository.get_all()

        assert len(documents) == len(sample_documents)

    async def test_get_all_with_status_filter(
        self, document_repository, sample_documents
    ):
        """Should filter documents by status."""
        # Create documents with different statuses
        doc1 = Document(content="Test1", title="Test1")
        doc1.status = DocumentStatus.COMPLETED
        doc2 = Document(content="Test2", title="Test2")
        doc2.status = DocumentStatus.PENDING

        await document_repository.create(doc1)
        await document_repository.create(doc2)

        pending_docs = await document_repository.get_all(status=DocumentStatus.PENDING)

        assert len(pending_docs) == 1
        assert pending_docs[0].status == DocumentStatus.PENDING

    async def test_update_document(self, document_repository, sample_document):
        """Should update an existing document."""
        created = await document_repository.create(sample_document)

        # Modify the document
        created.title = "Updated Title"
        created.mark_completed(chunk_count=10)

        updated = await document_repository.update(created)

        assert updated.title == "Updated Title"
        assert updated.status == DocumentStatus.COMPLETED
        assert updated.chunk_count == 10

    async def test_scope_and_is_public_round_trip(self, document_repository):
        """Should persist non-default scope and is_public across reload.

        Scenario: scope and is_public round-trip (AE-0090
        full-field document persistence Gherkin) — given a document with
        scope INTERNAL and is_public false, when saved and reloaded, then
        scope is INTERNAL and is_public is false.
        """
        document = Document(
            content="internal note",
            title="Internal",
            scope=DocumentScope.INTERNAL,
            is_public=False,
        )

        created = await document_repository.create(document)
        reloaded = await document_repository.get_by_id(created.id)

        assert reloaded is not None
        assert reloaded.scope == DocumentScope.INTERNAL
        assert reloaded.is_public is False

    async def test_scope_and_is_public_update_round_trip(
        self, document_repository, sample_document
    ):
        """Should persist scope/is_public changes via update_from_entity."""
        created = await document_repository.create(sample_document)
        assert created.scope == DocumentScope.PERSONAL
        assert created.is_public is False

        created.scope = DocumentScope.PUBLIC
        created.is_public = True
        created.mark_completed(chunk_count=3)
        await document_repository.update(created)

        reloaded = await document_repository.get_by_id(created.id)
        assert reloaded is not None
        assert reloaded.scope == DocumentScope.PUBLIC
        assert reloaded.is_public is True

    async def test_update_nonexistent_document(
        self, document_repository, sample_document
    ):
        """Should raise error when updating non-existent document."""
        # Create a document but don't save it
        document = sample_document
        document.id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await document_repository.update(document)

    async def test_delete_existing(self, document_repository, sample_document):
        """Should delete an existing document."""
        created = await document_repository.create(sample_document)

        deleted = await document_repository.delete(created.id)

        assert deleted is True

        # Verify deletion
        retrieved = await document_repository.get_by_id(created.id)
        assert retrieved is None

    async def test_delete_nonexistent(self, document_repository):
        """Should return False when deleting non-existent document."""
        deleted = await document_repository.delete(uuid4())

        assert deleted is False

    async def test_count_empty(self, document_repository):
        """Should return 0 when no documents exist."""
        count = await document_repository.count()

        assert count == 0

    async def test_count_with_documents(self, document_repository, sample_documents):
        """Should return correct document count."""
        for doc in sample_documents:
            await document_repository.create(doc)

        count = await document_repository.count()

        assert count == len(sample_documents)

    async def test_count_with_status_filter(self, document_repository):
        """Should count documents filtered by status."""
        doc1 = Document(content="Test1", title="Test1")
        doc1.status = DocumentStatus.COMPLETED
        doc2 = Document(content="Test2", title="Test2")
        doc2.status = DocumentStatus.PENDING
        doc3 = Document(content="Test3", title="Test3")
        doc3.status = DocumentStatus.PENDING

        await document_repository.create(doc1)
        await document_repository.create(doc2)
        await document_repository.create(doc3)

        pending_count = await document_repository.count(status=DocumentStatus.PENDING)
        completed_count = await document_repository.count(
            status=DocumentStatus.COMPLETED
        )

        assert pending_count == 2
        assert completed_count == 1
