"""SQLAlchemy ORM models for PostgreSQL."""

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

from rag_backend.domain.models import (
    CarouselProject as CarouselProjectEntity,
)
from rag_backend.domain.models import (
    CarouselSlide as CarouselSlideEntity,
)
from rag_backend.domain.models import (
    CarouselStatus,
    CarouselTheme,
    DocumentStatus,
    MessageRole,
    ResearchSourceType,
    UserRole,
)
from rag_backend.domain.models import (
    Conversation as ConversationEntity,
)
from rag_backend.domain.models import (
    Document as DocumentEntity,
)
from rag_backend.domain.models import (
    Message as MessageEntity,
)
from rag_backend.domain.models import (
    ResearchSource as ResearchSourceEntity,
)
from rag_backend.domain.models import (
    User as UserEntity,
)
from rag_backend.infrastructure.database.config import Base


class UserModel(Base):
    """SQLAlchemy model for User entity."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.EDITOR.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
    )

    def to_entity(self) -> UserEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return UserEntity(
            id=UUID(self.id),
            email=self.email,
            full_name=self.full_name,
            hashed_password=self.hashed_password,
            role=UserRole(self.role),
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: UserEntity) -> "UserModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            email=entity.email,
            full_name=entity.full_name,
            hashed_password=entity.hashed_password,
            role=entity.role.value,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class DocumentModel(Base):
    """SQLAlchemy model for Document entity."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    title = Column(String(500), nullable=False)
    doc_metadata = Column("metadata", JSON, default=dict, nullable=False)
    status = Column(String(20), default=DocumentStatus.PENDING.value, nullable=False)
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to owner
    owner = relationship("UserModel")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
        Index("idx_documents_updated_at", "updated_at"),
        Index("idx_documents_owner_id", "owner_id"),
    )

    def to_entity(self) -> DocumentEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return DocumentEntity(
            id=UUID(self.id),
            content=self.content,
            title=self.title,
            metadata=self.doc_metadata or {},
            status=DocumentStatus(self.status),
            error_message=self.error_message,
            chunk_count=self.chunk_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: DocumentEntity) -> "DocumentModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            content=entity.content,
            title=entity.title,
            doc_metadata=entity.metadata,
            status=entity.status.value,
            error_message=entity.error_message,
            chunk_count=entity.chunk_count,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_from_entity(self, entity: DocumentEntity) -> None:
        """Update ORM model from domain entity."""
        self.content = entity.content
        self.title = entity.title
        self.doc_metadata = entity.metadata
        self.status = entity.status.value
        self.error_message = entity.error_message
        self.chunk_count = entity.chunk_count
        self.updated_at = entity.updated_at


class ConversationModel(Base):
    """SQLAlchemy model for Conversation entity."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(500), nullable=True)
    conv_metadata = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to messages
    messages = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )

    # Relationship to owner
    owner = relationship("UserModel")

    __table_args__ = (
        Index("idx_conversations_updated_at", "updated_at"),
        Index("idx_conversations_owner_id", "owner_id"),
    )

    def to_entity(self) -> ConversationEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return ConversationEntity(
            id=UUID(self.id),
            title=self.title,
            metadata=self.conv_metadata or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: ConversationEntity) -> "ConversationModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            title=entity.title,
            conv_metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_from_entity(self, entity: ConversationEntity) -> None:
        """Update ORM model from domain entity."""
        self.title = entity.title
        self.conv_metadata = entity.metadata
        self.updated_at = entity.updated_at


class MessageModel(Base):
    """SQLAlchemy model for Message entity."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    msg_metadata = Column("metadata", JSON, default=dict, nullable=False)
    sources = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to conversation
    conversation = relationship("ConversationModel", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
    )

    def to_entity(self) -> MessageEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return MessageEntity(
            id=UUID(self.id),
            conversation_id=UUID(self.conversation_id),
            role=MessageRole(self.role),
            content=self.content,
            metadata=self.msg_metadata or {},
            sources=self.sources or [],
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: MessageEntity) -> "MessageModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            conversation_id=str(entity.conversation_id),
            role=entity.role.value,
            content=entity.content,
            msg_metadata=entity.metadata,
            sources=entity.sources,
            created_at=entity.created_at,
        )


class CarouselProjectModel(Base):
    """SQLAlchemy model for CarouselProject entity."""

    __tablename__ = "carousel_projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
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
    image_model = Column(String(30), nullable=False, server_default="gemini")
    image_style = Column(String(30), nullable=False, server_default="comic_neon")
    theme = Column(String(30), nullable=False, default=CarouselTheme.AUTO.value)
    primary_color = Column(String(20), nullable=True)
    accent_color = Column(String(20), nullable=True)
    background_color = Column(String(20), nullable=True)
    blog_markdown = Column(Text, nullable=True)
    blog_translations = Column(JSON, nullable=True)
    caption = Column(Text, nullable=True)
    linkedin_post_pt = Column(Text, nullable=True)
    linkedin_post_en = Column(Text, nullable=True)
    design_tokens = Column(
        JSON,
        nullable=True,
        comment="Complete visual design: colors, typography, images, layout",
    )
    status = Column(String(30), nullable=False, default=CarouselStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    output_dir = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    pdf_path_en = Column(String(500), nullable=True)
    phase_progress = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
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
            theme=CarouselTheme(self.theme),
            primary_color=self.primary_color,
            accent_color=self.accent_color,
            background_color=self.background_color,
            blog_markdown=self.blog_markdown,
            blog_translations=self.blog_translations,
            caption=self.caption,
            linkedin_post_pt=self.linkedin_post_pt,
            linkedin_post_en=self.linkedin_post_en,
            design_tokens=self.design_tokens,
            status=CarouselStatus(self.status),
            error_message=self.error_message,
            output_dir=self.output_dir,
            pdf_path=self.pdf_path,
            pdf_path_en=self.pdf_path_en,
            phase_progress=self.phase_progress,
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
            theme=entity.theme.value,
            primary_color=entity.primary_color,
            accent_color=entity.accent_color,
            background_color=entity.background_color,
            blog_markdown=entity.blog_markdown,
            blog_translations=entity.blog_translations,
            caption=entity.caption,
            linkedin_post_pt=entity.linkedin_post_pt,
            linkedin_post_en=entity.linkedin_post_en,
            design_tokens=entity.design_tokens,
            status=entity.status.value,
            error_message=entity.error_message,
            output_dir=entity.output_dir,
            pdf_path=entity.pdf_path,
            pdf_path_en=entity.pdf_path_en,
            phase_progress=entity.phase_progress,
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
        self.linkedin_post_pt = entity.linkedin_post_pt
        self.linkedin_post_en = entity.linkedin_post_en
        self.design_tokens = entity.design_tokens
        self.status = entity.status.value
        self.error_message = entity.error_message
        self.output_dir = entity.output_dir
        self.pdf_path = entity.pdf_path
        self.pdf_path_en = entity.pdf_path_en
        self.phase_progress = entity.phase_progress
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to project
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to project
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
