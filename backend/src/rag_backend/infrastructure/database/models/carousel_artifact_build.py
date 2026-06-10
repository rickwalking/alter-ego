"""SQLAlchemy model for carousel artifact build records."""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from rag_backend.domain.models.carousel_artifact_build import CarouselArtifactBuild
from rag_backend.infrastructure.database.config import Base


class CarouselArtifactBuildModel(Base):
    """Persisted artifact build attempt for export idempotency and recovery."""

    __tablename__ = "carousel_artifact_builds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("carousel_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_version = Column(String(80), nullable=False)
    operation_id = Column(String(64), nullable=False)
    source_lock_version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    staging_path = Column(String(500), nullable=True)
    error_json = Column(JSON, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_carousel_artifact_builds_project", "project_id"),
        Index("idx_carousel_artifact_builds_status", "status"),
    )

    def to_entity(self) -> CarouselArtifactBuild:
        return CarouselArtifactBuild(
            id=uuid.UUID(str(self.id)),
            project_id=uuid.UUID(str(self.project_id)),
            artifact_version=str(self.artifact_version),
            operation_id=str(self.operation_id),
            source_lock_version=int(self.source_lock_version),
            status=str(self.status),
            staging_path=self.staging_path,
            error_json=self.error_json,
            attempt_count=int(self.attempt_count),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: CarouselArtifactBuild) -> CarouselArtifactBuildModel:
        return cls(
            id=str(entity.id),
            project_id=str(entity.project_id),
            artifact_version=entity.artifact_version,
            operation_id=entity.operation_id,
            source_lock_version=entity.source_lock_version,
            status=entity.status,
            staging_path=entity.staging_path,
            error_json=entity.error_json,
            attempt_count=entity.attempt_count,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
