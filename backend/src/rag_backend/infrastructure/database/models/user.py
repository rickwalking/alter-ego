"""SQLAlchemy ORM model for User entity."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Index,
    String,
    false,
)

from rag_backend.domain.models import (
    User as UserEntity,
)
from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.columns import (
    created_at_column,
    updated_at_column,
)


class UserModel(Base):
    """SQLAlchemy model for User entity."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.EDITOR.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    created_at = created_at_column()
    updated_at = updated_at_column()

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
            must_change_password=bool(self.must_change_password),
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
            must_change_password=entity.must_change_password,
        )
