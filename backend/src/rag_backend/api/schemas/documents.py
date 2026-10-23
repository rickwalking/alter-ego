"""Document Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

DOCUMENT_TITLE_MAX_LENGTH = 500
DOCUMENT_SCOPE_MAX_LENGTH = 20
DOCUMENT_TAGS_MAX_LENGTH = 1000


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=DOCUMENT_TITLE_MAX_LENGTH)
    content: str = Field(..., min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    scope: str = Field(default="personal", max_length=DOCUMENT_SCOPE_MAX_LENGTH)
    is_public: bool = False


class DocumentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=DOCUMENT_TITLE_MAX_LENGTH)
    content: str | None = Field(None, min_length=1)
    metadata: dict[str, object] | None = None
    scope: str | None = Field(None, max_length=DOCUMENT_SCOPE_MAX_LENGTH)
    is_public: bool | None = None


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    status: str
    metadata: dict[str, object]
    chunk_count: int
    scope: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentProcessingStatus(BaseModel):
    id: UUID
    status: str
    chunk_count: int
    estimated_chunks: int
    estimated_time_seconds: float


class DocumentUploadResponse(BaseModel):
    id: UUID
    title: str
    status: str
    metadata: dict[str, object]
    chunk_count: int
    scope: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


class DocumentScopeChange(BaseModel):
    """The scope a document moves to (``personal`` or ``public``)."""

    scope: str = Field(..., min_length=1, max_length=DOCUMENT_SCOPE_MAX_LENGTH)
