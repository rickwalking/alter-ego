"""SQLAlchemy model for carousel image generation attempts."""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from rag_backend.domain.models import CarouselImageGeneration
from rag_backend.infrastructure.database.config import Base


class CarouselImageGenerationModel(Base):
    """Persisted image generation attempt for idempotency and recovery."""

    __tablename__ = "carousel_image_generations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("carousel_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_id = Column(
        String(36),
        ForeignKey("carousel_slides.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_number = Column(Integer, nullable=False)
    generation_key = Column(String(64), nullable=False, unique=True)
    status = Column(String(32), nullable=False)
    output_path = Column(String(500), nullable=True)
    prompt_hash = Column(String(64), nullable=True)
    provider = Column(String(30), nullable=True)
    model = Column(String(64), nullable=True)
    style = Column(String(64), nullable=True)
    raw_prompt = Column(Text, nullable=True)
    rendered_prompt = Column(Text, nullable=True)
    content_sha256 = Column(String(64), nullable=True)
    provider_image_id = Column(String(128), nullable=True)
    error_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_carousel_image_generations_project", "project_id"),
        Index("idx_carousel_image_generations_slide", "slide_id"),
        Index("idx_carousel_image_generations_status", "status"),
    )

    def to_entity(self) -> CarouselImageGeneration:
        return CarouselImageGeneration(
            id=uuid.UUID(str(self.id)),
            project_id=uuid.UUID(str(self.project_id)),
            slide_id=uuid.UUID(str(self.slide_id)),
            slide_number=int(self.slide_number),
            generation_key=str(self.generation_key),
            status=str(self.status),
            output_path=self.output_path,
            prompt_hash=self.prompt_hash,
            provider=self.provider,
            model=self.model,
            style=self.style,
            raw_prompt=self.raw_prompt,
            rendered_prompt=self.rendered_prompt,
            content_sha256=self.content_sha256,
            provider_image_id=self.provider_image_id,
            error_json=self.error_json,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(
        cls,
        entity: CarouselImageGeneration,
    ) -> CarouselImageGenerationModel:
        return cls(
            id=str(entity.id),
            project_id=str(entity.project_id),
            slide_id=str(entity.slide_id),
            slide_number=entity.slide_number,
            generation_key=entity.generation_key,
            status=entity.status,
            output_path=entity.output_path,
            prompt_hash=entity.prompt_hash,
            provider=entity.provider,
            model=entity.model,
            style=entity.style,
            raw_prompt=entity.raw_prompt,
            rendered_prompt=entity.rendered_prompt,
            content_sha256=entity.content_sha256,
            provider_image_id=entity.provider_image_id,
            error_json=entity.error_json,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_from_entity(self, entity: CarouselImageGeneration) -> None:
        self.status = entity.status
        self.output_path = entity.output_path
        self.prompt_hash = entity.prompt_hash
        self.provider = entity.provider
        self.model = entity.model
        self.style = entity.style
        self.raw_prompt = entity.raw_prompt
        self.rendered_prompt = entity.rendered_prompt
        self.content_sha256 = entity.content_sha256
        self.provider_image_id = entity.provider_image_id
        self.error_json = entity.error_json
        self.updated_at = entity.updated_at
