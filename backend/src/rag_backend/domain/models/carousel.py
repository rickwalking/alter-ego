from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TypedDict
from uuid import UUID, uuid4

from rag_backend.domain.constants import IMAGE_MODEL_DEFAULT, IMAGE_STYLE_DEFAULT


class DesignTokenColors(TypedDict):
    primary: str
    accent: str
    bg: str
    text: str
    text_muted: str
    text_dim: str
    border: str
    glow: str


class DesignTokenTypography(TypedDict):
    font_family_heading: str
    font_family_body: str
    font_family_badge: str


class DesignTokenImages(TypedDict, total=False):
    hero: str
    slides: list[str]
    rendered_slides_pt: list[str]
    rendered_slides_en: list[str]


class DesignTokenLayout(TypedDict):
    badge_label: str
    swipe_text: str
    progress_segments: int


class DesignTokens(TypedDict):
    colors: DesignTokenColors
    typography: DesignTokenTypography
    images: DesignTokenImages
    layout: DesignTokenLayout


class CarouselStatus(StrEnum):
    PENDING = "pending"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    DESIGNING = "designing"
    GENERATING_IMAGES = "generating_images"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class CarouselTheme(StrEnum):
    CYBERSECURITY = "cybersecurity"
    AI_COMPETITION = "ai_competition"
    DEVELOPER_SKILLS = "developer_skills"
    SOURCE_CODE = "source_code"
    SOCIAL_ENGINEERING = "social_engineering"
    AUTO = "auto"


class ResearchSourceType(StrEnum):
    TWITTER = "twitter"
    BLOG = "blog"
    REDDIT = "reddit"
    GITHUB = "github"
    NEWS = "news"
    DOCUMENTATION = "documentation"


@dataclass
class CarouselProject:
    topic: str
    audience: str
    niche: str
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    subtitle: str | None = None
    title_en: str | None = None
    subtitle_en: str | None = None
    slides_config: str = "1 intro, 3 content, 1 closing, 1 cta"
    aspect_ratio: str = "1080x1350"
    language: str = "pt-BR"
    generate_images: bool = True
    image_model: str = IMAGE_MODEL_DEFAULT
    image_style: str = IMAGE_STYLE_DEFAULT
    theme: CarouselTheme = CarouselTheme.AUTO
    primary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    blog_markdown: str | None = None
    blog_translations: dict[str, str] | None = None
    blog_image_map: list[dict[str, str | int]] | None = None
    caption: str | None = None
    linkedin_post_pt: str | None = None
    linkedin_post_en: str | None = None
    design_tokens: DesignTokens | None = None
    status: CarouselStatus = CarouselStatus.PENDING
    error_message: str | None = None
    output_dir: str | None = None
    pdf_path: str | None = None
    pdf_path_en: str | None = None
    phase_progress: dict[str, str | int | list[dict[str, str | int]]] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_status(self, status: CarouselStatus, error_message: str | None = None) -> None:
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def mark_completed(self, output_dir: str) -> None:
        self.status = CarouselStatus.COMPLETED
        self.output_dir = output_dir
        self.updated_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = CarouselStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def set_theme_colors(self, primary: str, accent: str, background: str) -> None:
        self.primary_color = primary
        self.accent_color = accent
        self.background_color = background

    def set_title(self, title: str, subtitle: str | None = None) -> None:
        self.title = title
        self.subtitle = subtitle
        self.updated_at = datetime.utcnow()

    def set_title_en(self, title: str, subtitle: str | None = None) -> None:
        self.title_en = title
        self.subtitle_en = subtitle
        self.updated_at = datetime.utcnow()

    def get_blog(self, language: str = "pt") -> str | None:
        if self.blog_translations and language in self.blog_translations:
            return self.blog_translations[language]
        return self.blog_markdown

    def get_available_languages(self) -> list[str]:
        if self.blog_translations:
            return list(self.blog_translations.keys())
        if self.blog_markdown:
            return ["pt"]
        return []

    def get_design(self) -> DesignTokens | None:
        return self.design_tokens

    def get_image_url(self, filename: str) -> str | None:
        if not self.output_dir:
            return None
        return f"/api/carousels/{self.id}/images/{filename}"


@dataclass
class CarouselSlide:
    project_id: UUID
    slide_number: int
    slide_type: str
    heading: str
    body: str
    id: UUID = field(default_factory=uuid4)
    html_content: str | None = None
    image_path: str | None = None
    image_prompt: str | None = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    extras: dict[str, object] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResearchSource:
    project_id: UUID
    source_url: str
    source_type: ResearchSourceType
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    extracted_content: str | None = None
    relevance_score: float = 0.0
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
