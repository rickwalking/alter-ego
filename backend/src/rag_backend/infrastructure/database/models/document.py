"""SQLAlchemy ORM model for Document entity."""

import uuid

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
    Document as DocumentEntity,
)
from rag_backend.domain.models import DocumentStatus
from rag_backend.infrastructure.database.config import Base


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

    owner = relationship("UserModel")

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
