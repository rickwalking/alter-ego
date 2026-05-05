"""SQLAlchemy ORM models for Conversation and Message entities."""

import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from rag_backend.domain.models import (
    Conversation as ConversationEntity,
)
from rag_backend.domain.models import (
    Message as MessageEntity,
)
from rag_backend.domain.models import MessageRole
from rag_backend.infrastructure.database.config import Base


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

    messages = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )

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
