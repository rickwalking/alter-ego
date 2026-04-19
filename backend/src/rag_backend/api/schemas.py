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


# ============== Carousel Schemas ==============

class CarouselProjectCreate(BaseModel):
    """Schema for creating a carousel project."""
    topic: str = Field(..., min_length=1, max_length=500)
    audience: str = Field(..., min_length=1, max_length=500)
    niche: str = Field(..., min_length=1, max_length=200)
    slides_config: str = Field(default="1 intro, 3 content, 1 closing, 1 cta", max_length=200)
    language: str = Field(default="pt-BR", max_length=10)
    generate_images: bool = True
    theme: str = Field(default="auto", max_length=30)


class CarouselProjectUpdate(BaseModel):
    """Schema for updating a carousel project."""
    title: Optional[str] = Field(None, max_length=500)
    subtitle: Optional[str] = None
    blog_markdown: Optional[str] = None
    caption: Optional[str] = None


class CarouselSlideResponse(BaseModel):
    """Schema for carousel slide response."""
    id: UUID
    slide_number: int
    slide_type: str
    heading: str
    body: str
    image_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchSourceResponse(BaseModel):
    """Schema for research source response."""
    id: UUID
    source_url: str
    source_type: str
    title: Optional[str] = None
    relevance_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CarouselProjectResponse(BaseModel):
    """Schema for carousel project response."""
    id: UUID
    topic: str
    audience: str
    niche: str
    title: Optional[str]
    subtitle: Optional[str]
    theme: str
    primary_color: Optional[str]
    accent_color: Optional[str]
    background_color: Optional[str]
    blog_markdown: Optional[str]
    caption: Optional[str]
    status: str
    error_message: Optional[str] = None
    output_dir: Optional[str] = None
    slides: list[CarouselSlideResponse] = Field(default_factory=list)
    research_sources: list[ResearchSourceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CarouselProjectListResponse(BaseModel):
    """Schema for list of carousel projects."""
    items: list[CarouselProjectResponse]
    total: int
    limit: int
    offset: int


class CarouselStatusResponse(BaseModel):
    """Schema for carousel generation status."""
    id: UUID
    status: str
    error_message: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class CarouselGenerateRequest(BaseModel):
    """Schema for triggering carousel generation."""
    sources: Optional[list[str]] = Field(default=None, description="Optional source URLs to research")


class CarouselCaptionResponse(BaseModel):
    """Schema for generated Instagram caption."""
    caption: str
    hashtags: list[str]


class CarouselBlogResponse(BaseModel):
    """Schema for generated blog post."""
    markdown: str
    title: str
    subtitle: Optional[str] = None
