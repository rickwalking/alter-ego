"""SQLAlchemy ORM model for BlogPost entity."""

import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.infrastructure.database.config import Base


class BlogPostModel(Base):
    """SQLAlchemy model for BlogPost entity."""

    __tablename__ = "blog_posts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("carousel_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Provenance (AE-0127): 'standalone' (hand-authored) vs 'carousel' (derived).
    origin = Column(
        String(20),
        default=BlogPostOrigin.STANDALONE.value,
        server_default=BlogPostOrigin.STANDALONE.value,
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default="draft", nullable=False)

    # Content
    content = Column(JSON, default=dict, nullable=False)
    excerpt = Column(String(500), nullable=True)
    featured_image_url = Column(String(500), nullable=True)

    # Editorial
    author_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    editor_comments = Column(JSON, default=list, nullable=False)
    version_history = Column(JSON, default=list, nullable=False)

    # Sources
    sources = Column(JSON, default=list, nullable=False)
    citations = Column(JSON, default=list, nullable=False)

    # AI Assistance
    ai_suggestions = Column(JSON, default=list, nullable=False)
    ai_generation_metadata = Column(JSON, default=dict, nullable=False)
    ai_disclosure_label = Column(String(50), default="none", nullable=True)

    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    keywords = Column(JSON, default=list, nullable=False)
    canonical_url = Column(String(500), nullable=True)

    # Engagement
    view_count = Column(Integer, default=0, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    share_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    submitted_for_review_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_publish_at = Column(DateTime(timezone=True), nullable=True)
    lock_version = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("idx_blog_posts_status", "status"),
        Index("idx_blog_posts_slug", "slug"),
        Index("idx_blog_posts_author", "author_id"),
        Index("idx_blog_posts_project", "project_id"),
        Index(
            "idx_blog_posts_author_status_updated", "author_id", "status", "updated_at"
        ),
    )

    content_sources = relationship(
        "ContentSourceModel",
        back_populates="blog_posts",
        cascade="all, delete-orphan",
    )

    def to_entity(self):
        """Convert ORM model to domain entity."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "origin": self.origin,
            "title": self.title,
            "slug": self.slug,
            "status": self.status,
            "content": self.content,
            "excerpt": self.excerpt,
            "featured_image_url": self.featured_image_url,
            "author_id": self.author_id,
            "reviewer_id": self.reviewer_id,
            "editor_comments": self.editor_comments,
            "version_history": self.version_history,
            "sources": self.sources,
            "citations": self.citations,
            "ai_suggestions": self.ai_suggestions,
            "ai_generation_metadata": self.ai_generation_metadata,
            "ai_disclosure_label": self.ai_disclosure_label,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "keywords": self.keywords,
            "canonical_url": self.canonical_url,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "submitted_for_review_at": self.submitted_for_review_at,
            "approved_at": self.approved_at,
            "published_at": self.published_at,
            "scheduled_publish_at": self.scheduled_publish_at,
            "lock_version": self.lock_version,
        }

    @classmethod
    def from_entity(cls, entity: dict) -> "BlogPostModel":
        """Create ORM model from domain entity."""
        return cls(
            id=entity.get("id", str(uuid.uuid4())),
            project_id=entity.get("project_id"),
            origin=entity.get("origin", BlogPostOrigin.STANDALONE.value),
            title=entity.get("title", ""),
            slug=entity.get("slug", ""),
            status=entity.get("status", "draft"),
            content=entity.get("content", {}),
            excerpt=entity.get("excerpt"),
            featured_image_url=entity.get("featured_image_url"),
            author_id=entity.get("author_id"),
            reviewer_id=entity.get("reviewer_id"),
            editor_comments=entity.get("editor_comments", []),
            version_history=entity.get("version_history", []),
            sources=entity.get("sources", []),
            citations=entity.get("citations", []),
            ai_suggestions=entity.get("ai_suggestions", []),
            ai_generation_metadata=entity.get("ai_generation_metadata", {}),
            ai_disclosure_label=entity.get("ai_disclosure_label", "none"),
            meta_title=entity.get("meta_title"),
            meta_description=entity.get("meta_description"),
            keywords=entity.get("keywords", []),
            canonical_url=entity.get("canonical_url"),
            view_count=entity.get("view_count", 0),
            like_count=entity.get("like_count", 0),
            comment_count=entity.get("comment_count", 0),
            share_count=entity.get("share_count", 0),
            created_at=entity.get("created_at"),
            updated_at=entity.get("updated_at"),
            submitted_for_review_at=entity.get("submitted_for_review_at"),
            approved_at=entity.get("approved_at"),
            published_at=entity.get("published_at"),
            scheduled_publish_at=entity.get("scheduled_publish_at"),
            lock_version=entity.get("lock_version", 1),
        )
