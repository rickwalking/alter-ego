"""Carousel Pydantic schemas."""

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


class CarouselProjectCreate(BaseModel):
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


class CarouselProjectResponse(BaseModel):
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
    design_tokens: dict[str, dict[str, str | int | list[str] | None]] | None = None
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
    items: list[CarouselProjectResponse]
    total: int
    limit: int
    offset: int


class CarouselStatusResponse(BaseModel):
    id: UUID
    status: str
    error_message: str | None = None
    phase_progress: dict[str, str | int | list[dict[str, str | int]]] | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class CarouselGenerateRequest(BaseModel):
    sources: list[str] | None = Field(default=None, description="Optional source URLs to research")


class InstagramPublishRequest(BaseModel):
    caption: str = Field(..., min_length=1, max_length=2200)


class InstagramPublishResponse(BaseModel):
    status: str
    ig_post_id: str | None = None
    error_message: str | None = None


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


class CarouselBlogImageMapEntry(BaseModel):
    slide_number: int
    heading: str
    alt: str


class CarouselDesignImages(BaseModel):
    hero: str
    slides: list[str]
    rendered_slides_pt: list[str] | None = None
    rendered_slides_en: list[str] | None = None
    blog_image_map: list[CarouselBlogImageMapEntry] | None = None


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
