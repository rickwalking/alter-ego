"""Unit tests for domain models."""

from rag_backend.domain.models import (
    Conversation,
    Document,
    DocumentChunk,
    DocumentStatus,
    Message,
    MessageRole,
    SearchResult,
)


class TestDocument:
    """Tests for Document entity."""

    def test_document_creation(self):
        """Document should be created with default values."""
        document = Document(
            content="Test content",
            title="Test Title",
        )

        assert document.content == "Test content"
        assert document.title == "Test Title"
        assert document.status == DocumentStatus.PENDING
        assert document.chunk_count == 0
        assert document.error_message is None
        assert document.metadata == {}

    def test_document_with_metadata(self):
        """Document should accept metadata dictionary."""
        metadata = {"category": "test", "tags": ["ai", "ml"]}
        document = Document(
            content="Test",
            title="Test",
            metadata=metadata,
        )

        assert document.metadata == metadata

    def test_update_status(self):
        """Document status can be updated."""
        document = Document(content="Test", title="Test")

        document.update_status(DocumentStatus.PROCESSING)
        assert document.status == DocumentStatus.PROCESSING

        document.update_status(DocumentStatus.FAILED, "Error occurred")
        assert document.status == DocumentStatus.FAILED
        assert document.error_message == "Error occurred"

    def test_mark_completed(self):
        """Document can be marked as completed."""
        document = Document(content="Test", title="Test")
        document.status = DocumentStatus.PROCESSING

        document.mark_completed(chunk_count=5)

        assert document.status == DocumentStatus.COMPLETED
        assert document.chunk_count == 5
        assert document.error_message is None

    def test_mark_failed(self):
        """Document can be marked as failed."""
        document = Document(content="Test", title="Test")

        document.mark_failed("Processing failed")

        assert document.status == DocumentStatus.FAILED
        assert document.error_message == "Processing failed"


class TestDocumentChunk:
    """Tests for DocumentChunk entity."""

    def test_chunk_creation(self):
        """Chunk should be created with required fields."""
        from uuid import uuid4

        document_id = uuid4()
        chunk = DocumentChunk(
            content="Chunk content",
            document_id=document_id,
            index=0,
        )

        assert chunk.content == "Chunk content"
        assert chunk.document_id == document_id
        assert chunk.index == 0
        assert chunk.dense_embedding is None
        assert chunk.sparse_embedding is None


class TestConversation:
    """Tests for Conversation entity."""

    def test_conversation_creation(self):
        """Conversation should be created with default values."""
        conversation = Conversation()

        assert conversation.title is None
        assert conversation.metadata == {}

    def test_update_title(self):
        """Conversation title can be updated."""
        conversation = Conversation()

        conversation.update_title("New Title")

        assert conversation.title == "New Title"

    def test_touch_updates_timestamp(self):
        """Touch should update the updated_at timestamp."""

        conversation = Conversation()
        old_updated_at = conversation.updated_at

        # Small delay to ensure timestamp changes
        import time

        time.sleep(0.001)

        conversation.touch()

        assert conversation.updated_at > old_updated_at


class TestMessage:
    """Tests for Message entity."""

    def test_message_creation(self):
        """Message should be created with required fields."""
        from uuid import uuid4

        conversation_id = uuid4()
        message = Message(
            role=MessageRole.USER,
            content="Hello",
            conversation_id=conversation_id,
        )

        assert message.role == MessageRole.USER
        assert message.content == "Hello"
        assert message.conversation_id == conversation_id
        assert message.sources == []
        assert message.metadata == {}


class TestSearchResult:
    """Tests for SearchResult entity."""

    def test_search_result_creation(self):
        """SearchResult should be created with required fields."""
        from uuid import uuid4

        document_id = uuid4()
        result = SearchResult(
            content="Result content",
            document_id=document_id,
            score=0.95,
        )

        assert result.content == "Result content"
        assert result.document_id == document_id
        assert result.score == 0.95
        assert result.rank == 0
        assert result.metadata == {}
