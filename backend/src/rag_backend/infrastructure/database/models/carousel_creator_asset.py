"""SQLAlchemy model for managed carousel creator assets."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.infrastructure.database.config import Base


class CarouselCreatorAssetModel(Base):
    """Persisted normalized creator avatar/branding asset."""

    __tablename__ = "carousel_creator_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_sha256 = Column(String(64), nullable=False)
    media_type = Column(String(64), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    relative_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_carousel_creator_assets_owner", "owner_id"),
        UniqueConstraint(
            "owner_id",
            "content_sha256",
            name="uq_carousel_creator_assets_owner_sha256",
        ),
    )

    def to_entity(self) -> CarouselCreatorAsset:
        return CarouselCreatorAsset(
            id=uuid.UUID(str(self.id)),
            owner_id=str(self.owner_id),
            content_sha256=str(self.content_sha256),
            media_type=str(self.media_type),
            width=int(self.width),
            height=int(self.height),
            relative_path=str(self.relative_path),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: CarouselCreatorAsset) -> CarouselCreatorAssetModel:
        return cls(
            id=str(entity.id),
            owner_id=entity.owner_id,
            content_sha256=entity.content_sha256,
            media_type=entity.media_type,
            width=entity.width,
            height=entity.height,
            relative_path=entity.relative_path,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
