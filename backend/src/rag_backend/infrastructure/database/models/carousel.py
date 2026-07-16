"""SQLAlchemy ORM models for CarouselProject, CarouselSlide, and ResearchSource entities."""

import uuid
from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rag_backend.domain.models import (
    CarouselProject as CarouselProjectEntity,
)
from rag_backend.domain.models import (
    CarouselSlide as CarouselSlideEntity,
)
from rag_backend.domain.models import CarouselStatus, CarouselTheme, ResearchSourceType
from rag_backend.domain.models import (
    ResearchSource as ResearchSourceEntity,
)
from rag_backend.infrastructure.database.config import Base


class CarouselProjectModel(Base):
    """SQLAlchemy model for CarouselProject entity."""

    __tablename__ = "carousel_projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    # Public-release (visibility) flag — written by the publishing release port
    # (AE-0128); SQLAlchemy 2.0 ``Mapped[...]`` so the instance attribute types as
    # ``bool`` for the byte-identical ``is_public=True`` release write.
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    topic = Column(String(500), nullable=False)
    audience = Column(String(500), nullable=False)
    niche = Column(String(200), nullable=False)
    title = Column(String(500), nullable=True)
    subtitle = Column(Text, nullable=True)
    title_en = Column(String(500), nullable=True)
    subtitle_en = Column(Text, nullable=True)
    slides_config = Column(
        String(200),
        nullable=False,
        default="1 intro, 3 content, 1 closing, 1 cta",
    )
    aspect_ratio = Column(String(20), nullable=False, default="1080x1350")
    language = Column(String(10), nullable=False, default="pt-BR")
    generate_images = Column(Integer, default=1, nullable=False)
    # AE-0308: openai is the only funded provider; comic_neon now runs on it.
    image_model = Column(String(30), nullable=False, server_default="openai")
    image_style = Column(String(30), nullable=False, server_default="comic_neon")
    # Widened to 64 (AE-0269 migration a7b8c9d0e1f2) to hold a custom-palette UUID.
    theme = Column(String(64), nullable=False, default=CarouselTheme.AUTO.value)
    # Resolved palette frozen at generation (AE-0269 D9).
    theme_snapshot = Column(JSON, nullable=True)
    primary_color = Column(String(20), nullable=True)
    accent_color = Column(String(20), nullable=True)
    background_color = Column(String(20), nullable=True)
    blog_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    blog_translations = Column(JSON, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_en = Column(Text, nullable=True)
    linkedin_post_pt: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_post_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    design_tokens = Column(
        JSON,
        nullable=True,
        comment="Complete visual design: colors, typography, images, layout",
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CarouselStatus.PENDING.value
    )
    # AE-0210: ``Mapped[...]`` so the auto-reject write types as ``str | None``.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_dir = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    pdf_path_en = Column(String(500), nullable=True)
    phase_progress = Column(JSON, nullable=True)

    # NEW: Workflow extension fields
    creative_brief = Column(Text, nullable=True)
    persona_id = Column(String(36), ForeignKey("persona_profiles.id"), nullable=True)
    assigned_reviewer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    rubric_id = Column(String(36), ForeignKey("quality_rubrics.id"), nullable=True)
    instructions = Column(Text, nullable=True)
    custom_visual_details = Column(Text, nullable=True)
    current_phase: Mapped[str | None] = mapped_column(String(50), default="brief")
    phase_status: Mapped[str | None] = mapped_column(String(50), default="pending")
    workflow_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="", server_default=""
    )
    lock_version = Column(Integer, default=1, nullable=False)

    # AE-0315: run-progress visibility + zombie fencing. ``run_started_at`` /
    # ``run_heartbeat_at`` are stamped when ``phase_status`` transitions INTO
    # ``in_progress`` and cleared ATOMICALLY (same flush UPDATE) on any
    # value-changing transition out of it — enforced by the ``before_update``
    # listener in ``infrastructure/database/carousel_run_guard.py``, not per
    # call site. ``run_epoch`` is the monotonic fencing token; only the
    # stale-run reaper increments it. Deliberately NOT mapped onto the domain
    # entity so the ``update_from_entity`` hydrator can never clobber them.
    run_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    run_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    run_epoch: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # AE-0314: server-guaranteed republish marker. Stamped in the SAME
    # transaction as a post-completion slide-text edit; the workflow watchdog
    # republishes any marked project older than a few minutes and clears it, so
    # a corrected carousel never keeps serving a stale PDF (cold-critic r6).
    # Deliberately NOT mapped onto the domain entity (like the run columns) so
    # the ``update_from_entity`` hydrator can never clobber it.
    needs_republish_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Creator watermark metadata
    creator_name = Column(String(100), nullable=True)
    creator_handle = Column(String(100), nullable=True)
    creator_avatar_url = Column(String(500), nullable=True)
    creator_website = Column(String(500), nullable=True)
    creator_asset_id = Column(
        String(36),
        ForeignKey("carousel_creator_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    presentation_policy_version = Column(String(64), nullable=True)
    presentation_policy_checksum = Column(String(80), nullable=True)
    artifact_version = Column(String(80), nullable=True)
    slide_layout_strategy = Column(String(50), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    slides = relationship(
        "CarouselSlideModel",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="CarouselSlideModel.slide_number",
    )
    research_sources = relationship(
        "ResearchSourceModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_carousel_projects_status", "status"),
        Index("idx_carousel_projects_created_at", "created_at"),
        Index("idx_carousel_projects_updated_at", "updated_at"),
    )

    def to_entity(self) -> CarouselProjectEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return CarouselProjectEntity(
            id=UUID(self.id),
            topic=self.topic,
            audience=self.audience,
            niche=self.niche,
            title=self.title,
            subtitle=self.subtitle,
            title_en=self.title_en,
            subtitle_en=self.subtitle_en,
            slides_config=self.slides_config,
            aspect_ratio=self.aspect_ratio,
            language=self.language,
            generate_images=bool(self.generate_images),
            image_model=self.image_model,
            image_style=self.image_style,
            theme=self.theme,
            theme_snapshot=self.theme_snapshot,
            primary_color=self.primary_color,
            accent_color=self.accent_color,
            background_color=self.background_color,
            blog_markdown=self.blog_markdown,
            blog_translations=self.blog_translations,
            caption=self.caption,
            caption_en=self.caption_en,
            linkedin_post_pt=self.linkedin_post_pt,
            linkedin_post_en=self.linkedin_post_en,
            design_tokens=self.design_tokens,
            status=CarouselStatus(self.status),
            error_message=self.error_message,
            output_dir=self.output_dir,
            pdf_path=self.pdf_path,
            pdf_path_en=self.pdf_path_en,
            phase_progress=self.phase_progress,
            # NEW: workflow extension fields
            creative_brief=self.creative_brief,
            persona_id=self.persona_id,
            rubric_id=self.rubric_id,
            instructions=self.instructions,
            custom_visual_details=self.custom_visual_details,
            current_phase=self.current_phase,
            phase_status=self.phase_status,
            is_public=bool(self.is_public),
            owner_id=self.owner_id,
            creator_name=self.creator_name,
            creator_handle=self.creator_handle,
            creator_avatar_url=self.creator_avatar_url,
            creator_website=self.creator_website,
            creator_asset_id=UUID(self.creator_asset_id)
            if self.creator_asset_id
            else None,
            presentation_policy_version=self.presentation_policy_version,
            presentation_policy_checksum=self.presentation_policy_checksum,
            artifact_version=self.artifact_version,
            slide_layout_strategy=self.slide_layout_strategy,
            # AE-0314: read-only marker (never written back via update_from_entity).
            needs_republish_since=self.needs_republish_since,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: CarouselProjectEntity) -> "CarouselProjectModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            topic=entity.topic,
            audience=entity.audience,
            niche=entity.niche,
            title=entity.title,
            subtitle=entity.subtitle,
            title_en=entity.title_en,
            subtitle_en=entity.subtitle_en,
            slides_config=entity.slides_config,
            aspect_ratio=entity.aspect_ratio,
            language=entity.language,
            generate_images=1 if entity.generate_images else 0,
            image_model=entity.image_model,
            image_style=entity.image_style,
            theme=entity.theme,
            theme_snapshot=entity.theme_snapshot,
            primary_color=entity.primary_color,
            accent_color=entity.accent_color,
            background_color=entity.background_color,
            blog_markdown=entity.blog_markdown,
            blog_translations=entity.blog_translations,
            caption=entity.caption,
            caption_en=entity.caption_en,
            linkedin_post_pt=entity.linkedin_post_pt,
            linkedin_post_en=entity.linkedin_post_en,
            design_tokens=entity.design_tokens,
            status=entity.status.value,
            error_message=entity.error_message,
            output_dir=entity.output_dir,
            pdf_path=entity.pdf_path,
            pdf_path_en=entity.pdf_path_en,
            phase_progress=entity.phase_progress,
            # NEW: workflow extension fields
            creative_brief=entity.creative_brief,
            persona_id=entity.persona_id,
            rubric_id=entity.rubric_id,
            instructions=entity.instructions,
            custom_visual_details=entity.custom_visual_details,
            current_phase=entity.current_phase,
            phase_status=entity.phase_status,
            is_public=entity.is_public,
            owner_id=entity.owner_id,
            creator_name=entity.creator_name,
            creator_handle=entity.creator_handle,
            creator_avatar_url=entity.creator_avatar_url,
            creator_website=entity.creator_website,
            creator_asset_id=str(entity.creator_asset_id)
            if entity.creator_asset_id
            else None,
            presentation_policy_version=entity.presentation_policy_version,
            presentation_policy_checksum=entity.presentation_policy_checksum,
            artifact_version=entity.artifact_version,
            slide_layout_strategy=entity.slide_layout_strategy,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_from_entity(self, entity: CarouselProjectEntity) -> None:
        """Update ORM model from domain entity."""
        self.title = entity.title
        self.subtitle = entity.subtitle
        self.title_en = entity.title_en
        self.subtitle_en = entity.subtitle_en
        self.primary_color = entity.primary_color
        self.accent_color = entity.accent_color
        self.background_color = entity.background_color
        self.blog_markdown = entity.blog_markdown
        self.blog_translations = entity.blog_translations
        self.caption = entity.caption
        self.caption_en = entity.caption_en
        self.linkedin_post_pt = entity.linkedin_post_pt
        self.linkedin_post_en = entity.linkedin_post_en
        self.design_tokens = entity.design_tokens
        self.status = entity.status.value
        self.error_message = entity.error_message
        self.output_dir = entity.output_dir
        self.pdf_path = entity.pdf_path
        self.pdf_path_en = entity.pdf_path_en
        self.phase_progress = entity.phase_progress
        # NEW: workflow extension fields
        self.creative_brief = entity.creative_brief
        self.persona_id = entity.persona_id
        self.rubric_id = entity.rubric_id
        self.instructions = entity.instructions
        self.custom_visual_details = entity.custom_visual_details
        self.theme_snapshot = entity.theme_snapshot
        self.current_phase = entity.current_phase
        self.phase_status = entity.phase_status
        self.is_public = entity.is_public
        self.owner_id = entity.owner_id
        self.creator_name = entity.creator_name
        self.creator_handle = entity.creator_handle
        self.creator_avatar_url = entity.creator_avatar_url
        self.creator_website = entity.creator_website
        self.creator_asset_id = (
            str(entity.creator_asset_id) if entity.creator_asset_id else None
        )
        self.presentation_policy_version = entity.presentation_policy_version
        self.presentation_policy_checksum = entity.presentation_policy_checksum
        self.artifact_version = entity.artifact_version
        self.slide_layout_strategy = entity.slide_layout_strategy
        self.updated_at = entity.updated_at


class CarouselSlideModel(Base):
    """SQLAlchemy model for CarouselSlide entity."""

    __tablename__ = "carousel_slides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("carousel_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_number = Column(Integer, nullable=False)
    slide_type = Column(String(20), nullable=False)
    heading = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    html_content = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    image_prompt = Column(Text, nullable=True)
    slide_metadata = Column("metadata", JSON, default=dict, nullable=False)
    extras = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project = relationship("CarouselProjectModel", back_populates="slides")

    __table_args__ = (
        Index("idx_carousel_slides_project_id", "project_id"),
        Index("idx_carousel_slides_number", "project_id", "slide_number", unique=True),
    )

    def to_entity(self) -> CarouselSlideEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return CarouselSlideEntity(
            id=UUID(self.id),
            project_id=UUID(self.project_id),
            slide_number=self.slide_number,
            slide_type=self.slide_type,
            heading=self.heading,
            body=self.body,
            html_content=self.html_content,
            image_path=self.image_path,
            image_prompt=self.image_prompt,
            metadata=self.slide_metadata or {},
            extras=self.extras,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: CarouselSlideEntity) -> "CarouselSlideModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            project_id=str(entity.project_id),
            slide_number=entity.slide_number,
            slide_type=entity.slide_type,
            heading=entity.heading,
            body=entity.body,
            html_content=entity.html_content,
            image_path=entity.image_path,
            image_prompt=entity.image_prompt,
            slide_metadata=entity.metadata,
            extras=entity.extras,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_from_entity(self, entity: CarouselSlideEntity) -> None:
        """Update ORM model from domain entity."""
        self.slide_number = entity.slide_number
        self.slide_type = entity.slide_type
        self.heading = entity.heading
        self.body = entity.body
        self.html_content = entity.html_content
        self.image_path = entity.image_path
        self.image_prompt = entity.image_prompt
        self.slide_metadata = entity.metadata
        self.extras = entity.extras
        self.updated_at = entity.updated_at


class ResearchSourceModel(Base):
    """SQLAlchemy model for ResearchSource entity."""

    __tablename__ = "research_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("carousel_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url = Column(String(1000), nullable=False)
    source_type = Column(String(30), nullable=False)
    title = Column(String(500), nullable=True)
    extracted_content = Column(Text, nullable=True)
    relevance_score = Column(Integer, default=0, nullable=False)
    source_metadata = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship("CarouselProjectModel", back_populates="research_sources")

    __table_args__ = (
        Index("idx_research_sources_project_id", "project_id"),
        Index("idx_research_sources_type", "source_type"),
    )

    def to_entity(self) -> ResearchSourceEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return ResearchSourceEntity(
            id=UUID(self.id),
            project_id=UUID(self.project_id),
            source_url=self.source_url,
            source_type=ResearchSourceType(self.source_type),
            title=self.title,
            extracted_content=self.extracted_content,
            relevance_score=float(self.relevance_score),
            metadata=self.source_metadata or {},
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: ResearchSourceEntity) -> "ResearchSourceModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            project_id=str(entity.project_id),
            source_url=entity.source_url,
            source_type=entity.source_type.value,
            title=entity.title,
            extracted_content=entity.extracted_content,
            relevance_score=int(entity.relevance_score),
            source_metadata=entity.metadata,
            created_at=entity.created_at,
        )
