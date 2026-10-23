"""Carousel Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rag_backend.api.schemas.carousel_content_mode import (
    ContentModeRequestFields,
    ContentModeResponseFields,
)
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


class CarouselProjectCreate(ContentModeRequestFields):
    """Request body that creates a carousel project.

    theme is a root key, "auto" or a custom-palette UUID (36 chars), stored as a string
    reference in a varchar(64) column. rubric_id is the quality rubric (left out: the
    default carousel rubric; null: none).
    """

    topic: str = Field(..., min_length=1, max_length=500)
    audience: str = Field(..., min_length=1, max_length=500)
    niche: str = Field(..., min_length=1, max_length=200)
    slides_config: str = Field(
        default="1 intro, 3 content, 1 closing, 1 cta", max_length=200
    )
    language: str = Field(default="pt-BR", max_length=10)
    generate_images: bool = True
    theme: str = Field(default="auto", max_length=64)
    image_model: str = Field(default=IMAGE_MODEL_DEFAULT, max_length=30)
    image_style: str = Field(default=IMAGE_STYLE_DEFAULT, max_length=30)
    custom_visual_details: str | None = Field(None, max_length=500)
    strategy: str | None = Field(None, max_length=50)
    rubric_id: UUID | None = None

    @field_validator("theme")
    @classmethod
    def _check_theme(cls, value: str) -> str:
        from rag_backend.domain.models.carousel import validate_theme_reference

        return validate_theme_reference(value)

    @field_validator("image_model")
    @classmethod
    def _check_image_model(cls, value: str) -> str:
        if value not in VALID_IMAGE_MODELS:
            raise ValueError(
                _ERR_INVALID_IMAGE_MODEL.format(sorted(VALID_IMAGE_MODELS), value)
            )
        return value

    @field_validator("image_style")
    @classmethod
    def _check_image_style(cls, value: str) -> str:
        if value not in VALID_IMAGE_STYLES:
            raise ValueError(
                _ERR_INVALID_IMAGE_STYLE.format(sorted(VALID_IMAGE_STYLES), value)
            )
        return value

    @model_validator(mode="after")
    def _check_combo(self) -> "CarouselProjectCreate":
        if (self.image_model, self.image_style) not in SUPPORTED_IMAGE_COMBOS:
            raise ValueError(
                _ERR_UNSUPPORTED_IMAGE_COMBO.format(
                    self.image_model, self.image_style, sorted(SUPPORTED_IMAGE_COMBOS)
                )
            )
        self.check_content_mode()
        return self


class CarouselProjectUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    subtitle: str | None = None
    blog_markdown: str | None = None
    caption: str | None = None


class CarouselSlideResponse(BaseModel):
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
    id: UUID
    source_url: str
    source_type: str
    title: str | None = None
    relevance_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CarouselProjectResponse(ContentModeResponseFields):
    """Carousel project as returned by the API.

    language lets the public gallery label a card without an extra design or slides
    request. custom_visual_details echoes the request-side scene guidance so it survives
    a reload. needs_republish_since is set while a post-completion edit still owes a PDF
    rebuild; the publish page shows a "rebuild pending" state until the watchdog or the
    client republishes and clears it.
    """

    id: UUID
    topic: str
    audience: str
    niche: str
    language: str
    title: str | None
    subtitle: str | None
    title_en: str | None = None
    subtitle_en: str | None = None
    theme: str
    image_model: str = IMAGE_MODEL_DEFAULT
    image_style: str = IMAGE_STYLE_DEFAULT
    custom_visual_details: str | None = None
    primary_color: str | None
    accent_color: str | None
    background_color: str | None
    blog_markdown: str | None
    blog_translations: dict[str, str] | None = None
    caption: str | None
    linkedin_post_pt: str | None = None
    linkedin_post_en: str | None = None
    design_tokens: dict[str, dict[str, str | int | list[str] | None]] | None = None
    status: str
    error_message: str | None = None
    output_dir: str | None = None
    pdf_path: str | None = None
    pdf_path_en: str | None = None
    creator_name: str | None = None
    creator_handle: str | None = None
    creator_avatar_url: str | None = None
    template_version: str | None = None
    slide_layout_strategy: str | None = None
    rubric_id: str | None = None
    is_public: bool = False
    current_phase: str | None = None
    phase_status: str | None = None
    needs_republish_since: datetime | None = None
    slides: list[CarouselSlideResponse] = Field(default_factory=list)
    research_sources: list[ResearchSourceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CarouselProjectListResponse(BaseModel):
    items: list[CarouselProjectResponse]
    total: int
    limit: int
    offset: int


class CarouselPublicSlide(BaseModel):
    """One slide in the anonymous public viewer.

    Only the number, its heading (for alt text), and the public image URL. The
    owner-only ``image_path`` / preview URL never enters this projection.
    """

    slide_number: int
    heading: str | None = None
    image_url: str


class CarouselPublicResponse(BaseModel):
    """Lean public projection of a published carousel.

    ``topic`` is the title of last resort for carousels that never got one.
    """

    id: UUID
    topic: str | None = None
    title: str | None = None
    title_en: str | None = None
    subtitle: str | None = None
    subtitle_en: str | None = None
    language: str
    created_at: datetime
    slide_count: int
    available_languages: list[str]
    slides_by_language: dict[str, list[CarouselPublicSlide]]
    cover_url: str | None = None


class CarouselRepublishResponse(BaseModel):
    """Result of an idempotent artifact republish."""

    project_id: str
    status: str
    artifact_version: str | None = None
    pdf_path: str | None = None
    pdf_path_en: str | None = None


class InstagramPublishRequest(BaseModel):
    """Optional echo of the caption the page shows.

    The publish always sends the saved caption; a ``caption`` that differs from
    it is refused with 409 ``caption_not_saved`` instead of being published.
    """

    caption: str | None = Field(default=None, max_length=2200)


class InstagramPublishResponse(BaseModel):
    status: str
    ig_post_id: str | None = None
    error_message: str | None = None


class InstagramPublishStatusResponse(BaseModel):
    """Persisted Instagram publish state. Matches the frontend status path."""

    state: str
    ig_post_id: str | None = None
    permalink: str | None = None
    error: str | None = None


class CarouselCaptionResponse(BaseModel):
    caption: str
    hashtags: list[str]


class CarouselBlogResponse(BaseModel):
    markdown: str
    title: str
    subtitle: str | None = None


class CarouselBlogI18nResponse(BaseModel):
    markdown: str
    title: str
    subtitle: str | None
    language: str
    available_languages: list[str]

    model_config = {"from_attributes": False}


class CarouselDesignColors(BaseModel):
    primary: str
    accent: str
    bg: str
    text: str
    text_muted: str
    text_dim: str
    border: str
    glow: str


class CarouselDesignTypography(BaseModel):
    font_family_heading: str
    font_family_body: str
    font_family_badge: str


class CarouselDesignImages(BaseModel):
    hero: str
    slides: list[str]
    rendered_slides_pt: list[str] | None = None
    rendered_slides_en: list[str] | None = None


class CarouselDesignLayout(BaseModel):
    badge_label: str
    swipe_text: str
    progress_segments: int


class CarouselDesignResponse(BaseModel):
    colors: CarouselDesignColors
    typography: CarouselDesignTypography
    images: CarouselDesignImages
    layout: CarouselDesignLayout
    theme_name: str

    model_config = {"from_attributes": False}


class CarouselBlogWithDesignResponse(BaseModel):
    markdown: str
    title: str
    subtitle: str | None
    language: str
    available_languages: list[str]
    design: CarouselDesignResponse

    model_config = {"from_attributes": False}
