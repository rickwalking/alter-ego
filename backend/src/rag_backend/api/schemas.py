"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from rag_backend.domain.constants import (
    IMAGE_MODEL_DEFAULT,
    IMAGE_STYLE_DEFAULT,
    SUPPORTED_IMAGE_COMBOS,
    VALID_IMAGE_MODELS,
    VALID_IMAGE_STYLES,
)

_ERR_INVALID_IMAGE_MODEL = "image_model must be one of {}, got {!r}"
_ERR_INVALID_IMAGE_STYLE = "image_style must be one of {}, got {!r}"
_ERR_UNSUPPORTED_IMAGE_COMBO = (
    "image_model={!r} with image_style={!r} is not supported. Allowed: {}"
)

# ============== Document Schemas ==============


class DocumentBase(BaseModel):
    """Base document schema."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    metadata: dict[str, object] | None = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: UUID
    title: str
    status: str
    metadata: dict[str, object]
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

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

    title: str | None = Field(None, max_length=500)
    metadata: dict[str, object] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""

    title: str | None = Field(None, max_length=500)
    metadata: dict[str, object] | None = None


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: UUID
    title: str | None
    metadata: dict[str, object]
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
    metadata: dict[str, object]
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

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
    content: str | None = None
    sources: list[MessageSource] | None = None


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
    metadata: dict[str, object]


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
    details: dict[str, object] | None = None


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
    image_model: str = Field(default=IMAGE_MODEL_DEFAULT, max_length=30)
    image_style: str = Field(default=IMAGE_STYLE_DEFAULT, max_length=30)

    @field_validator("image_model")
    @classmethod
    def _check_image_model(cls, value: str) -> str:
        if value not in VALID_IMAGE_MODELS:
            raise ValueError(_ERR_INVALID_IMAGE_MODEL.format(sorted(VALID_IMAGE_MODELS), value))
        return value

    @field_validator("image_style")
    @classmethod
    def _check_image_style(cls, value: str) -> str:
        if value not in VALID_IMAGE_STYLES:
            raise ValueError(_ERR_INVALID_IMAGE_STYLE.format(sorted(VALID_IMAGE_STYLES), value))
        return value

    @model_validator(mode="after")
    def _check_combo(self) -> "CarouselProjectCreate":
        if (self.image_model, self.image_style) not in SUPPORTED_IMAGE_COMBOS:
            raise ValueError(
                _ERR_UNSUPPORTED_IMAGE_COMBO.format(
                    self.image_model, self.image_style, sorted(SUPPORTED_IMAGE_COMBOS)
                )
            )
        return self


class CarouselProjectUpdate(BaseModel):
    """Schema for updating a carousel project."""

    title: str | None = Field(None, max_length=500)
    subtitle: str | None = None
    blog_markdown: str | None = None
    caption: str | None = None


class CarouselSlideResponse(BaseModel):
    """Schema for carousel slide response."""

    id: UUID
    slide_number: int
    slide_type: str
    heading: str
    body: str
    image_path: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchSourceResponse(BaseModel):
    """Schema for research source response."""

    id: UUID
    source_url: str
    source_type: str
    title: str | None = None
    relevance_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CarouselProjectResponse(BaseModel):
    """Schema for carousel project response."""

    id: UUID
    topic: str
    audience: str
    niche: str
    title: str | None
    subtitle: str | None
    title_en: str | None = None
    subtitle_en: str | None = None
    theme: str
    image_model: str = IMAGE_MODEL_DEFAULT
    image_style: str = IMAGE_STYLE_DEFAULT
    primary_color: str | None
    accent_color: str | None
    background_color: str | None
    blog_markdown: str | None
    blog_translations: dict[str, str] | None = None
    caption: str | None
    linkedin_post_pt: str | None = None
    linkedin_post_en: str | None = None
    design_tokens: dict[str, dict[str, str | int | list[str]]] | None = None
    status: str
    error_message: str | None = None
    output_dir: str | None = None
    pdf_path: str | None = None
    pdf_path_en: str | None = None
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
    error_message: str | None = None
    phase_progress: dict[str, str | int | list[dict[str, str | int]]] | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class CarouselGenerateRequest(BaseModel):
    """Schema for triggering carousel generation."""

    sources: list[str] | None = Field(default=None, description="Optional source URLs to research")


class InstagramPublishRequest(BaseModel):
    """Schema for the Instagram publish route body."""

    caption: str = Field(..., min_length=1, max_length=2200)


class InstagramPublishResponse(BaseModel):
    """Schema for the Instagram publish result."""

    status: str  # "queued" | "published" | "failed"
    ig_post_id: str | None = None
    error_message: str | None = None


class CarouselCaptionResponse(BaseModel):
    """Schema for generated Instagram caption."""

    caption: str
    hashtags: list[str]


class CarouselBlogResponse(BaseModel):
    """Schema for generated blog post."""

    markdown: str
    title: str
    subtitle: str | None = None


class CarouselBlogI18nResponse(BaseModel):
    """Schema for localized blog post response."""

    markdown: str
    title: str
    subtitle: str | None
    language: str
    available_languages: list[str]

    model_config = {"from_attributes": False}


class CarouselDesignColors(BaseModel):
    """Schema for design token colors."""

    primary: str
    accent: str
    bg: str
    text: str
    text_muted: str
    text_dim: str
    border: str
    glow: str


class CarouselDesignTypography(BaseModel):
    """Schema for design token typography."""

    font_family_heading: str
    font_family_body: str
    font_family_badge: str


class CarouselBlogImageMapEntry(BaseModel):
    """Single entry mapping a blog H2 heading to a carousel slide image."""

    slide_number: int
    heading: str
    alt: str


class CarouselDesignImages(BaseModel):
    """Schema for design token images.

    `hero` + `slides` are the raw OpenAI/Gemini hero JPGs (used by the
    blog). `rendered_slides_pt` / `rendered_slides_en` are the post-
    Playwright renders with text overlay (used by the publish viewer).
    `blog_image_map` tells the frontend which slide image belongs to
    each blog section heading.
    """

    hero: str
    slides: list[str]
    rendered_slides_pt: list[str] | None = None
    rendered_slides_en: list[str] | None = None
    blog_image_map: list[CarouselBlogImageMapEntry] | None = None


class CarouselDesignLayout(BaseModel):
    """Schema for design token layout."""

    badge_label: str
    swipe_text: str
    progress_segments: int


class CarouselDesignResponse(BaseModel):
    """Complete visual design tokens for a blog post."""

    colors: CarouselDesignColors
    typography: CarouselDesignTypography
    images: CarouselDesignImages
    layout: CarouselDesignLayout
    theme_name: str

    model_config = {"from_attributes": False}


class CarouselBlogWithDesignResponse(BaseModel):
    """Blog post response with inline design tokens."""

    markdown: str
    title: str
    subtitle: str | None
    language: str
    available_languages: list[str]
    design: CarouselDesignResponse

    model_config = {"from_attributes": False}
