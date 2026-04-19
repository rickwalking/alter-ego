"""Domain entities for the RAG system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Document:
    """Represents a document in the knowledge base."""

    content: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    chunk_count: int = 0

    def update_status(
        self, status: DocumentStatus, error_message: Optional[str] = None
    ) -> None:
        """Update document status and timestamp."""
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def mark_completed(self, chunk_count: int) -> None:
        """Mark document as successfully processed."""
        self.status = DocumentStatus.COMPLETED
        self.chunk_count = chunk_count
        self.updated_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """Mark document as failed with error."""
        self.status = DocumentStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()


@dataclass
class DocumentChunk:
    """Represents a chunk of a document for vector storage."""

    content: str
    document_id: UUID
    index: int
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)
    dense_embedding: Optional[list[float]] = None
    sparse_embedding: Optional[dict[str, Any]] = None


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a message in a conversation."""

    role: MessageRole
    content: str
    conversation_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Conversation:
    """Represents a conversation session."""

    id: UUID = field(default_factory=uuid4)
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_title(self, title: str) -> None:
        """Update conversation title."""
        self.title = title
        self.updated_at = datetime.utcnow()

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


@dataclass
class SearchResult:
    """Represents a search result from hybrid retrieval."""

    content: str
    document_id: UUID
    score: float
    chunk_id: Optional[UUID] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    rank: int = 0
