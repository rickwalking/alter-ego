"""Domain entities for the RAG system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class DocumentStatus(str, Enum):
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
    error_message: Optional[str] = None
    chunk_count: int = 0

    def update_status(
        self, status: DocumentStatus, error_message: Optional[str] = None
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
    dense_embedding: Optional[list[float]] = None
    sparse_embedding: Optional[dict[str, float]] = None


class MessageRole(str, Enum):
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
    title: Optional[str] = None
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
    chunk_id: Optional[UUID] = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    rank: int = 0


# =============================================================================
# Carousel Content Pipeline Models
# =============================================================================


class CarouselStatus(str, Enum):
    """Carousel project generation status."""

    PENDING = "pending"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    DESIGNING = "designing"
    GENERATING_IMAGES = "generating_images"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class CarouselTheme(str, Enum):
    """Predefined carousel color themes."""

    CYBERSECURITY = "cybersecurity"
    AI_COMPETITION = "ai_competition"
    DEVELOPER_SKILLS = "developer_skills"
    SOURCE_CODE = "source_code"
    SOCIAL_ENGINEERING = "social_engineering"
    AUTO = "auto"


class ResearchSourceType(str, Enum):
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
    title: Optional[str] = None
    subtitle: Optional[str] = None
    slides_config: str = "1 intro, 3 content, 1 closing, 1 cta"
    aspect_ratio: str = "1080x1350"
    language: str = "pt-BR"
    generate_images: bool = True
    theme: CarouselTheme = CarouselTheme.AUTO
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    blog_markdown: Optional[str] = None
    caption: Optional[str] = None
    status: CarouselStatus = CarouselStatus.PENDING
    error_message: Optional[str] = None
    output_dir: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_status(
        self, status: CarouselStatus, error_message: Optional[str] = None
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

    def set_title(self, title: str, subtitle: Optional[str] = None) -> None:
        """Set the optimized title."""
        self.title = title
        self.subtitle = subtitle
        self.updated_at = datetime.utcnow()


@dataclass
class CarouselSlide:
    """Represents a single slide in a carousel."""

    project_id: UUID
    slide_number: int
    slide_type: str  # "intro", "content", "closing", "cta"
    heading: str
    body: str
    id: UUID = field(default_factory=uuid4)
    html_content: Optional[str] = None
    image_path: Optional[str] = None
    image_prompt: Optional[str] = None
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
    title: Optional[str] = None
    extracted_content: Optional[str] = None
    relevance_score: float = 0.0
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
