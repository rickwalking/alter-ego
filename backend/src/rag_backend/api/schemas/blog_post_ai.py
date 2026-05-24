"""Pydantic schemas for blog post AI assistance endpoints."""

from pydantic import BaseModel, Field


class BlogPostAiSuggestRequest(BaseModel):
    """Request body for AI suggestion generation."""

    text: str = Field(..., min_length=1, max_length=10000)
    suggestion_type: str = Field(default="improve", min_length=1, max_length=50)
    context: str | None = Field(default=None, max_length=10000)


class BlogPostAiSuggestResponse(BaseModel):
    """AI suggestion response."""

    original_text: str
    suggested_text: str
    suggestion_type: str
    explanation: str


class BlogPostAiImproveRequest(BaseModel):
    """Request body for AI text improvement."""

    text: str = Field(..., min_length=1, max_length=10000)
    action: str = Field(default="improve", min_length=1, max_length=50)
    context: str | None = Field(default=None, max_length=10000)
    persona_id: str | None = None


class BlogPostAiImproveResponse(BaseModel):
    """AI improvement response."""

    original_text: str
    improved_text: str
    action: str


class BlogPostGenerateImageRequest(BaseModel):
    """Request body for blog featured image generation."""

    prompt: str = Field(..., min_length=1, max_length=2000)


class BlogPostGenerateImageResponse(BaseModel):
    """Generated blog image response."""

    prompt: str
    image_url: str


__all__ = [
    "BlogPostAiImproveRequest",
    "BlogPostAiImproveResponse",
    "BlogPostAiSuggestRequest",
    "BlogPostAiSuggestResponse",
    "BlogPostGenerateImageRequest",
    "BlogPostGenerateImageResponse",
]
