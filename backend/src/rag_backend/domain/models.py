"""Domain entities for the RAG system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TypedDict
from uuid import UUID, uuid4


class DesignTokenColors(TypedDict):
    """Design token colors for blog post styling."""

    primary: str
    accent: str
    bg: str
    text: str
    text_muted: str
    text_dim: str
    border: str
    glow: str


class DesignTokenTypography(TypedDict):
    """Design token typography for blog post styling."""

    font_family_heading: str
    font_family_body: str
    font_family_badge: str


class DesignTokenImages(TypedDict):
    """Design token image URLs for blog post."""

    hero: str
    slides: list[str]


class DesignTokenLayout(TypedDict):
    """Design token layout properties for blog post."""

    badge_label: str
    swipe_text: str
    progress_segments: int


class DesignTokens(TypedDict):
    """Complete visual design tokens for a blog post / carousel."""

    colors: DesignTokenColors
    typography: DesignTokenTypography
    images: DesignTokenImages
    layout: DesignTokenLayout


class DocumentStatus(StrEnum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Document:
    """Represents a document in the knowledge base."""

    content: str
    title: str
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: str | None = None
    chunk_count: int = 0

    def update_status(
        self, status: DocumentStatus, error_message: str | None = None
    ) -> None:
        """Update document status and timestamp."""
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def mark_completed(self, chunk_count: int) -> None:
        """Mark document as successfully processed."""
        self.status = DocumentStatus.COMPLETED
        self.chunk_count = chunk_count
        self.updated_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """Mark document as failed with error."""
        self.status = DocumentStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()


@dataclass
class DocumentChunk:
    """Represents a chunk of a document for vector storage."""

    content: str
    document_id: UUID
    index: int
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    dense_embedding: list[float] | None = None
    sparse_embedding: dict[str, float] | None = None


class MessageRole(StrEnum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a message in a conversation."""

    role: MessageRole
    content: str
    conversation_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    sources: list[dict[str, str | int | float | bool]] = field(default_factory=list)


@dataclass
class Conversation:
    """Represents a conversation session."""

    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def update_title(self, title: str) -> None:
        """Update conversation title."""
        self.title = title
        self.updated_at = datetime.utcnow()

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


@dataclass
class SearchResult:
    """Represents a search result from hybrid retrieval."""

    content: str
    document_id: UUID
    score: float
    chunk_id: UUID | None = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    rank: int = 0


# =============================================================================
# Carousel Content Pipeline Models
# =============================================================================


class CarouselStatus(StrEnum):
    """Carousel project generation status."""

    PENDING = "pending"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    DESIGNING = "designing"
    GENERATING_IMAGES = "generating_images"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class CarouselTheme(StrEnum):
    """Predefined carousel color themes."""

    CYBERSECURITY = "cybersecurity"
    AI_COMPETITION = "ai_competition"
    DEVELOPER_SKILLS = "developer_skills"
    SOURCE_CODE = "source_code"
    SOCIAL_ENGINEERING = "social_engineering"
    AUTO = "auto"


class ResearchSourceType(StrEnum):
    """Types of research sources."""

    TWITTER = "twitter"
    BLOG = "blog"
    REDDIT = "reddit"
    GITHUB = "github"
    NEWS = "news"
    DOCUMENTATION = "documentation"


@dataclass
class CarouselProject:
    """Represents a carousel content generation project."""

    topic: str
    audience: str
    niche: str
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    subtitle: str | None = None
    slides_config: str = "1 intro, 3 content, 1 closing, 1 cta"
    aspect_ratio: str = "1080x1350"
    language: str = "pt-BR"
    generate_images: bool = True
    theme: CarouselTheme = CarouselTheme.AUTO
    primary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    blog_markdown: str | None = None
    blog_translations: dict[str, str] | None = None
    caption: str | None = None
    design_tokens: DesignTokens | None = None
    status: CarouselStatus = CarouselStatus.PENDING
    error_message: str | None = None
    output_dir: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_status(
        self, status: CarouselStatus, error_message: str | None = None
    ) -> None:
        """Update project status and timestamp."""
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def mark_completed(self, output_dir: str) -> None:
        """Mark project as successfully generated."""
        self.status = CarouselStatus.COMPLETED
        self.output_dir = output_dir
        self.updated_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """Mark project as failed with error."""
        self.status = CarouselStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def set_theme_colors(
        self, primary: str, accent: str, background: str
    ) -> None:
        """Set the color palette for this carousel."""
        self.primary_color = primary
        self.accent_color = accent
        self.background_color = background

    def set_title(self, title: str, subtitle: str | None = None) -> None:
        """Set the optimized title."""
        self.title = title
        self.subtitle = subtitle
        self.updated_at = datetime.utcnow()

    def get_blog(self, language: str = "pt") -> str | None:
        """Get blog markdown for a specific language."""
        if self.blog_translations and language in self.blog_translations:
            return self.blog_translations[language]
        return self.blog_markdown

    def get_available_languages(self) -> list[str]:
        """Return list of available blog languages."""
        if self.blog_translations:
            return list(self.blog_translations.keys())
        if self.blog_markdown:
            return ["pt"]
        return []

    def get_design(self) -> DesignTokens | None:
        """Return complete design tokens for frontend consumption."""
        return self.design_tokens

    def get_image_url(self, filename: str) -> str | None:
        """Get the API URL for a carousel image."""
        if not self.output_dir:
            return None
        return f"/api/carousels/{self.id}/images/{filename}"


@dataclass
class CarouselSlide:
    """Represents a single slide in a carousel."""

    project_id: UUID
    slide_number: int
    slide_type: str  # "intro", "content", "closing", "cta"
    heading: str
    body: str
    id: UUID = field(default_factory=uuid4)
    html_content: str | None = None
    image_path: str | None = None
    image_prompt: str | None = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResearchSource:
    """Represents a source used during carousel research."""

    project_id: UUID
    source_url: str
    source_type: ResearchSourceType
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    extracted_content: str | None = None
    relevance_score: float = 0.0
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
