"""Domain models for Content Sources and Editorial Comments."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TypedDict
from uuid import UUID, uuid4


class SourceType(StrEnum):
    """Types of content sources."""
    URL = "url"
    DOCUMENT = "document"
    NOTE = "note"
    INTERVIEW = "interview"
    DATA = "data"


@dataclass
class ContentSource:
    """A content source for a project or blog post."""
    id: UUID = field(default_factory=uuid4)
    project_id: UUID | None = None
    blog_post_id: UUID | None = None
    source_type: SourceType = SourceType.URL
    title: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    extracted_key_points: list[str] = field(default_factory=list)
    is_primary: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_key_point(self, point: str) -> None:
        """Add an extracted key point."""
        if point and point not in self.extracted_key_points:
            self.extracted_key_points.append(point)
            self.updated_at = datetime.utcnow()

    def add_tag(self, tag: str) -> None:
        """Add a tag."""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()


@dataclass
class EditorialComment:
    """An editorial comment on content."""
    id: UUID = field(default_factory=uuid4)
    content_id: UUID = field(default_factory=uuid4)
    content_type: str = ""
    author_id: str = ""
    text: str = ""
    position: dict = field(default_factory=dict)
    status: str = "open"
    ai_suggestion: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None

    def mark_resolved(self) -> None:
        """Mark the comment as resolved."""
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()

    def mark_dismissed(self) -> None:
        """Mark the comment as dismissed."""
        self.status = "dismissed"
        self.resolved_at = datetime.utcnow()


@dataclass
class ContentVersion:
    """A version of content for tracking changes."""
    id: UUID = field(default_factory=uuid4)
    content_id: UUID = field(default_factory=uuid4)
    content_type: str = ""
    version_number: int = 0
    snapshot: dict = field(default_factory=dict)
    change_summary: str = ""
    author_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
