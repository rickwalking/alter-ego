"""Domain models for carousel workflow."""

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
    """Status values for carousel workflow lifecycle."""

    PENDING = "pending"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    DESIGNING = "designing"
    GENERATING_IMAGES = "generating_images"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class CarouselTheme(StrEnum):
    """Predefined themes for carousel content generation."""

    CYBERSECURITY = "cybersecurity"
    AI_COMPETITION = "ai_competition"
    DEVELOPER_SKILLS = "developer_skills"
    SOURCE_CODE = "source_code"
    SOCIAL_ENGINEERING = "social_engineering"
    # Dark variants (pair with the neon/neo-anime image styles).
    PLASMA_MAGENTA = "plasma_magenta"
    ACID_LIME = "acid_lime"
    MONO_INDIGO = "mono_indigo"
    EMBER_CRIMSON = "ember_crimson"
    BLUEPRINT = "blueprint"
    # Light / editorial palettes (pair with the flat_editorial image style).
    RISOGRAPH = "risograph"
    PAPER_EDITORIAL = "paper_editorial"
    CLINICAL_MINT = "clinical_mint"
    AUTO = "auto"


def validate_theme_reference(ref: str) -> str:
    """Validate a project ``theme`` reference and return it (AE-0268/0271).

    A theme is a root key, the ``"auto"`` sentinel, or a **custom-palette UUID**.
    Custom palettes cannot be enum members, so a UUID-shaped reference is accepted
    here; whether it points at a live palette is resolved at generation (the D9
    snapshot resolver, which degrades gracefully), not at creation. Raises
    ``ValueError`` for anything that is neither a known root key/auto nor a UUID.
    """
    try:
        return CarouselTheme(ref).value
    except ValueError:
        pass
    try:
        UUID(ref)
    except ValueError as exc:
        msg = f"theme must be a root key, 'auto', or a custom palette id: {ref!r}"
        raise ValueError(msg) from exc
    return ref


class ResearchSourceType(StrEnum):
    """Source types for research data collection."""

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
    # Theme is a string reference (AE-0268): a root palette key, the "auto"
    # sentinel, or (from AE-0269) a custom palette UUID. The CarouselTheme enum
    # is retained as the canonical root-key list, not as this field's type.
    theme: str = CarouselTheme.AUTO.value
    # Resolved palette frozen at generation (AE-0269 D9): keys primary/accent/
    # background/mode/resolved_ref/resolved_at. Render reads this snapshot, not a
    # live lookup, so palette edits never alter an already-generated carousel.
    theme_snapshot: dict[str, str] | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    blog_markdown: str | None = None
    blog_translations: dict[str, str] | None = None
    blog_image_map: list[dict[str, str | int]] | None = None
    caption: str | None = None
    caption_en: str | None = None
    linkedin_post_pt: str | None = None
    linkedin_post_en: str | None = None
    design_tokens: DesignTokens | None = None
    status: CarouselStatus = CarouselStatus.PENDING
    error_message: str | None = None
    output_dir: str | None = None
    pdf_path: str | None = None
    pdf_path_en: str | None = None
    phase_progress: dict[str, str | int | list[dict[str, str | int]]] | None = None
    creative_brief: str | None = None
    persona_id: str | None = None
    rubric_id: str | None = None
    instructions: str | None = None
    # Project-level visual direction injected into every slide image prompt
    # (AE-0263 backdrop / custom scene details). Image-phase revision feedback
    # is appended here so a revision actually changes the rendered scene (AE-0261).
    custom_visual_details: str | None = None
    current_phase: str = "brief"
    phase_status: str = "pending"
    is_public: bool = False
    owner_id: str | None = None
    # Creator watermark metadata
    creator_name: str | None = None
    creator_handle: str | None = None
    creator_avatar_url: str | None = None
    creator_website: str | None = None
    creator_asset_id: UUID | None = None
    creator_asset_staged_path: str | None = None
    presentation_policy_version: str | None = None
    presentation_policy_checksum: str | None = None
    artifact_version: str | None = None
    # Template version for A/B testing and rollback
    template_version: str = "v2"
    # Slide layout strategy for visual formatting
    slide_layout_strategy: str | None = None
    # AE-0314: read-only view of the server-guaranteed republish marker. Written
    # ONLY by the write owner (mark/clear); never round-tripped through the ORM
    # ``update_from_entity`` hydrator, so it cannot be clobbered.
    needs_republish_since: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_status(
        self, status: CarouselStatus, error_message: str | None = None
    ) -> None:
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
