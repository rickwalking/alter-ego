"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============== Document Schemas ==============

class DocumentBase(BaseModel):
    """Base document schema."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[dict[str, Any]] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: UUID
    title: str
    status: str
    metadata: dict[str, Any]
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema for list of documents."""
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentProcessingStatus(BaseModel):
    """Schema for document processing status."""
    id: UUID
    status: str
    chunk_count: int
    estimated_chunks: int
    estimated_time_seconds: float


# ============== Conversation Schemas ==============

class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""
    title: Optional[str] = Field(None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict[str, Any]] = None


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    id: UUID
    title: Optional[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """Schema for list of conversations."""
    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int


# ============== Message Schemas ==============

class MessageSource(BaseModel):
    """Schema for message source attribution."""
    document_id: UUID
    document_title: str
    content: str
    score: float


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: UUID
    role: str
    content: str
    sources: list[MessageSource] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """Schema for list of messages."""
    items: list[MessageResponse]
    conversation_id: UUID


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    id: UUID
    title: str
    status: str
    metadata: dict[str, Any]
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


# ============== Chat Schemas ==============

class ChatRequest(BaseModel):
    """Schema for sending a chat message."""
    content: str = Field(..., min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    """Schema for non-streaming chat response."""
    content: str
    sources: list[MessageSource] = Field(default_factory=list)
    conversation_id: UUID


class ChatMessageRequest(BaseModel):
    """Schema for sending a chat message."""
    content: str = Field(..., min_length=1, max_length=10000)


class ChatStreamResponse(BaseModel):
    """Schema for streaming chat response."""
    type: str  # 'token', 'sources', 'complete', 'error'
    content: Optional[str] = None
    sources: Optional[list[MessageSource]] = None


# ============== Search Schemas ==============

class SearchRequest(BaseModel):
    """Schema for search request."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchResultResponse(BaseModel):
    """Schema for search result."""
    content: str
    document_id: UUID
    document_title: str
    score: float
    rank: int
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Schema for search response."""
    query: str
    results: list[SearchResultResponse]
    total: int


# ============== Error Schemas ==============

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    message: str
    details: Optional[dict[str, Any]] = None


# ============== Health Schemas ==============

class HealthResponse(BaseModel):
    """Schema for basic health check response."""
    status: str
    version: str
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    """Schema for detailed readiness check response."""
    status: str
    version: str
    timestamp: datetime
    checks: dict[str, dict[str, str | int]]
