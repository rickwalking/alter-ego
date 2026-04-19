"""SQLAlchemy ORM models for PostgreSQL."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
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
    Conversation as ConversationEntity,
    Document as DocumentEntity,
    DocumentStatus,
    Message as MessageEntity,
    MessageRole,
)
from rag_backend.infrastructure.database.config import Base


class DocumentModel(Base):
    """SQLAlchemy model for Document entity."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    title = Column(String(500), nullable=False)
    doc_metadata = Column("metadata", JSON, default=dict, nullable=False)
    status = Column(String(20), default=DocumentStatus.PENDING.value, nullable=False)
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
        Index("idx_documents_updated_at", "updated_at"),
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
    title = Column(String(500), nullable=True)
    conv_metadata = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
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

    __table_args__ = (Index("idx_conversations_updated_at", "updated_at"),)

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
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

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
