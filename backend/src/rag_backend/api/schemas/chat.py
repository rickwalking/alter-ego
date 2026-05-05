"""Chat and search Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(None, max_length=500)
    metadata: dict[str, object] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    metadata: dict[str, object] | None = None


class ConversationResponse(BaseModel):
    id: UUID
    title: str | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int


class MessageSource(BaseModel):
    document_id: UUID
    document_title: str
    content: str
    score: float


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list[MessageSource] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    conversation_id: UUID


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    content: str
    sources: list[MessageSource] = Field(default_factory=list)
    conversation_id: UUID


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ChatStreamResponse(BaseModel):
    type: str
    content: str | None = None
    sources: list[MessageSource] | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchResultResponse(BaseModel):
    content: str
    document_id: UUID
    document_title: str
    score: float
    rank: int
    metadata: dict[str, object]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]
    total: int
