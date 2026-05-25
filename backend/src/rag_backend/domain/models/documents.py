from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentScope(StrEnum):
    PERSONAL = "personal"
    PUBLIC = "public"
    CAROUSEL = "carousel"
    INTERNAL = "internal"


@dataclass
class Document:
    content: str
    title: str
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: str | None = None
    chunk_count: int = 0
    scope: DocumentScope = DocumentScope.PERSONAL
    owner_id: UUID | None = None
    is_public: bool = False

    def update_status(self, status: DocumentStatus, error_message: str | None = None) -> None:
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def mark_completed(self, chunk_count: int) -> None:
        self.status = DocumentStatus.COMPLETED
        self.chunk_count = chunk_count
        self.updated_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()


@dataclass
class DocumentChunk:
    content: str
    document_id: UUID
    index: int
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    dense_embedding: list[float] | None = None
    sparse_embedding: dict[str, float] | None = None


@dataclass
class SearchResult:
    content: str
    document_id: UUID
    score: float
    chunk_id: UUID | None = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    rank: int = 0


@dataclass
class RetrievalQuery:
    query: str
    top_k: int = 5
    alpha: float = 0.5
    filters: dict[str, str | int | float | bool] | None = None
    namespace_prefix: str | None = None
