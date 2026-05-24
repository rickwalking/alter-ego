"""SQLAlchemy ORM models for ContentSource, EditorialComment, and ContentVersion entities."""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from rag_backend.infrastructure.database.config import Base


class ContentSourceModel(Base):
    """SQLAlchemy model for ContentSource entity."""

    __tablename__ = "content_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("carousel_projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    blog_post_id = Column(
        String(36),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    source_type = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_metadata = Column("metadata", JSON, default=dict, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    extracted_key_points = Column(JSON, default=list, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_content_sources_project_id", "project_id"),
        Index("idx_content_sources_blog_post_id", "blog_post_id"),
        Index("idx_content_sources_type", "source_type"),
    )

    blog_posts = relationship("BlogPostModel", back_populates="content_sources")


class EditorialCommentModel(Base):
    """SQLAlchemy model for EditorialComment entity."""

    __tablename__ = "editorial_comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String(36), nullable=False)
    content_type = Column(String(50), nullable=False)
    author_id = Column(String(36), nullable=False)
    text = Column(Text, nullable=False)
    position = Column(JSON, nullable=True)
    status = Column(String(20), default="open", nullable=False)
    ai_suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_editorial_comments_content_id", "content_id"),
        Index("idx_editorial_comments_status", "status"),
    )


class ContentVersionModel(Base):
    """SQLAlchemy model for ContentVersion entity."""

    __tablename__ = "content_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String(36), nullable=False)
    content_type = Column(String(30), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    change_summary = Column(String(500), nullable=True)
    author_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_content_versions_content_id", "content_id"),
        Index("idx_content_versions_type", "content_type"),
        Index("idx_content_versions_version", "content_type", "version_number", unique=True),
    )
