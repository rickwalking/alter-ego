"""Pydantic schemas for Blog Post management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BlogPostCreate(BaseModel):
    """Schema for creating a blog post."""

    title: str = Field(..., min_length=1, max_length=255)
    slug: str | None = None
    content: dict = Field(default_factory=dict)
    excerpt: str | None = None
    featured_image_url: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    author_id: str | None = None
    sources: list[str] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)


class BlogPostUpdate(BaseModel):
    """Schema for updating a blog post."""

    title: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = None
    content: dict | None = None
    excerpt: str | None = None
    featured_image_url: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    keywords: list[str] | None = None
    author_id: str | None = None
    reviewer_id: str | None = None
    status: str | None = None
    sources: list[str] | None = None
    citations: list[dict] | None = None


class BlogPostResponse(BaseModel):
    """Schema for blog post response."""

    id: UUID
    project_id: UUID | None = None
    title: str
    slug: str
    status: str
    content: dict
    excerpt: str | None = None
    featured_image_url: str | None = None
    author_id: str | None = None
    reviewer_id: str | None = None
    editor_comments: list[str] = Field(default_factory=list)
    version_history: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    ai_suggestions: list[dict] = Field(default_factory=list)
    ai_generation_metadata: dict = Field(default_factory=dict)
    ai_disclosure_label: str | None = "none"
    meta_title: str | None = None
    meta_description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    canonical_url: str | None = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    created_at: datetime
    updated_at: datetime
    submitted_for_review_at: datetime | None = None
    approved_at: datetime | None = None
    published_at: datetime | None = None
    scheduled_publish_at: datetime | None = None
    lock_version: int = 1

    class Config:
        from_attributes = True


class BlogPostSummaryResponse(BaseModel):
    """Lightweight blog post for list views (PERF-001)."""

    id: UUID
    title: str
    slug: str
    status: str
    excerpt: str | None = None
    featured_image_url: str | None = None
    author_id: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    lock_version: int = 1

    class Config:
        from_attributes = True


class BlogPostListResponse(BaseModel):
    """Schema for listing blog posts."""

    items: list[BlogPostSummaryResponse]
    total: int
    limit: int = 50
    offset: int = 0


class BlogPostVersionResponse(BaseModel):
    """Schema for blog post version response."""

    id: UUID
    version_number: int
    snapshot: dict
    change_summary: str | None = None
    author_id: str | None = None
    created_at: datetime


class EditorialCommentCreate(BaseModel):
    """Schema for creating an editorial comment."""

    content_id: UUID
    content_type: str
    text: str
    position: dict | None = None
    ai_suggestion: str | None = None


class EditorialCommentUpdate(BaseModel):
    """Schema for updating an editorial comment."""

    text: str | None = None
    status: str | None = None
    ai_suggestion: str | None = None


class EditorialCommentResponse(BaseModel):
    """Schema for editorial comment response."""

    id: UUID
    content_id: UUID
    content_type: str
    author_id: str
    text: str
    position: dict | None = None
    status: str
    ai_suggestion: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True


class EditorialCommentListResponse(BaseModel):
    """Schema for listing editorial comments."""

    items: list[EditorialCommentResponse]
    total: int


class ContentSourceCreate(BaseModel):
    """Schema for creating a content source."""

    project_id: UUID | None = None
    blog_post_id: UUID | None = None
    source_type: str = "url"  # url, document, note, interview, data
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    is_primary: bool = False
    created_by: str = ""


class ContentSourceResponse(BaseModel):
    """Schema for content source response."""

    id: UUID
    project_id: UUID | None = None
    blog_post_id: UUID | None = None
    source_type: str
    title: str
    content: str
    content_metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    extracted_key_points: list[str] = Field(default_factory=list)
    is_primary: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentSourceListResponse(BaseModel):
    """Schema for listing content sources."""

    items: list[ContentSourceResponse]
    total: int


class ContentVersionResponse(BaseModel):
    """Schema for content version response."""

    id: UUID
    content_id: UUID
    content_type: str
    version_number: int
    snapshot: dict
    change_summary: str | None = None
    author_id: str | None = None
    created_at: datetime


__all__ = [
    "BlogPostCreate",
    "BlogPostListResponse",
    "BlogPostResponse",
    "BlogPostSummaryResponse",
    "BlogPostUpdate",
    "BlogPostVersionResponse",
    "ContentSourceCreate",
    "ContentSourceListResponse",
    "ContentSourceResponse",
    "ContentVersionResponse",
    "EditorialCommentCreate",
    "EditorialCommentListResponse",
    "EditorialCommentResponse",
]
