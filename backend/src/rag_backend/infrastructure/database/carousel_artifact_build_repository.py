"""PostgreSQL repository for carousel artifact build records."""

from __future__ import annotations

from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.artifact_build import ERR_ARTIFACT_BUILD_CONFLICT
from rag_backend.domain.constants.carousel_presentation import (
    ARTIFACT_BUILD_STATUS_ACTIVE,
    ARTIFACT_BUILD_STATUS_FAILED,
    ARTIFACT_BUILD_STATUS_READY,
    ARTIFACT_BUILD_STATUS_STAGING,
    ARTIFACT_BUILD_STATUS_SUPERSEDED,
)
from rag_backend.domain.models.carousel_artifact_build import CarouselArtifactBuild
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.carousel_artifact_build import (
    CarouselArtifactBuildModel,
)


class _ActivateBuildParams(TypedDict, total=False):
    """Bundled parameters for activate_build."""

    project_id: UUID
    artifact_version: str
    source_lock_version: int
    prior_artifact_version: str | None


class PostgresCarouselArtifactBuildRepository:
    """Persistence helpers for artifact build lifecycle records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_project_and_version(
        self,
        project_id: UUID,
        artifact_version: str,
    ) -> CarouselArtifactBuild | None:
        stmt = select(CarouselArtifactBuildModel).where(
            CarouselArtifactBuildModel.project_id == str(project_id),
            CarouselArtifactBuildModel.artifact_version == artifact_version,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def get_active_build(self, project_id: UUID) -> CarouselArtifactBuild | None:
        stmt = (
            select(CarouselArtifactBuildModel)
            .where(
                CarouselArtifactBuildModel.project_id == str(project_id),
                CarouselArtifactBuildModel.status == ARTIFACT_BUILD_STATUS_ACTIVE,
            )
            .order_by(CarouselArtifactBuildModel.updated_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def upsert_build(self, build: CarouselArtifactBuild) -> CarouselArtifactBuild:
        existing = await self.get_by_project_and_version(
            build.project_id,
            build.artifact_version,
        )
        if existing is None:
            model = CarouselArtifactBuildModel.from_entity(build)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return model.to_entity()
        stmt = (
            update(CarouselArtifactBuildModel)
            .where(
                CarouselArtifactBuildModel.id == str(existing.id),
            )
            .values(
                status=build.status,
                staging_path=build.staging_path,
                error_json=build.error_json,
                attempt_count=build.attempt_count,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        refreshed = await self.get_by_project_and_version(
            build.project_id,
            build.artifact_version,
        )
        if refreshed is None:
            raise ValueError(ERR_ARTIFACT_BUILD_CONFLICT)
        return refreshed

    async def activate_build(
        self,
        *,
        params: _ActivateBuildParams,
    ) -> int:
        """Compare-and-swap activation; returns the new lock_version."""
        project_id = params["project_id"]
        artifact_version = params["artifact_version"]
        source_lock_version = params["source_lock_version"]
        prior_artifact_version = params.get("prior_artifact_version")

        project = await self._session.get(CarouselProjectModel, str(project_id))
        if project is None:
            raise ValueError(ERR_ARTIFACT_BUILD_CONFLICT)
        current_lock = int(project.lock_version or 1)
        current_artifact = project.artifact_version
        if current_lock != source_lock_version:
            raise ValueError(ERR_ARTIFACT_BUILD_CONFLICT)
        if current_artifact != prior_artifact_version:
            raise ValueError(ERR_ARTIFACT_BUILD_CONFLICT)

        new_lock = current_lock + 1
        project_result = await self._session.execute(
            update(CarouselProjectModel)
            .where(
                CarouselProjectModel.id == str(project_id),
                CarouselProjectModel.lock_version == source_lock_version,
                CarouselProjectModel.artifact_version == prior_artifact_version,
            )
            .values(
                artifact_version=artifact_version,
                lock_version=new_lock,
            )
        )
        if cast(CursorResult[object], project_result).rowcount != 1:
            raise ValueError(ERR_ARTIFACT_BUILD_CONFLICT)

        if prior_artifact_version and prior_artifact_version != artifact_version:
            await self._session.execute(
                update(CarouselArtifactBuildModel)
                .where(
                    CarouselArtifactBuildModel.project_id == str(project_id),
                    CarouselArtifactBuildModel.artifact_version
                    == prior_artifact_version,
                    CarouselArtifactBuildModel.status == ARTIFACT_BUILD_STATUS_ACTIVE,
                )
                .values(status=ARTIFACT_BUILD_STATUS_SUPERSEDED)
            )

        build_result = await self._session.execute(
            update(CarouselArtifactBuildModel)
            .where(
                CarouselArtifactBuildModel.project_id == str(project_id),
                CarouselArtifactBuildModel.artifact_version == artifact_version,
            )
            .values(status=ARTIFACT_BUILD_STATUS_ACTIVE)
        )
        if cast(CursorResult[object], build_result).rowcount != 1:
            raise ValueError(ERR_ARTIFACT_BUILD_CONFLICT)
        await self._session.flush()
        return new_lock

    async def mark_build_status(
        self,
        project_id: UUID,
        artifact_version: str,
        status: str,
    ) -> None:
        await self._session.execute(
            update(CarouselArtifactBuildModel)
            .where(
                CarouselArtifactBuildModel.project_id == str(project_id),
                CarouselArtifactBuildModel.artifact_version == artifact_version,
            )
            .values(status=status)
        )
        await self._session.flush()


__all__ = [
    "ARTIFACT_BUILD_STATUS_ACTIVE",
    "ARTIFACT_BUILD_STATUS_FAILED",
    "ARTIFACT_BUILD_STATUS_READY",
    "ARTIFACT_BUILD_STATUS_STAGING",
    "ARTIFACT_BUILD_STATUS_SUPERSEDED",
    "PostgresCarouselArtifactBuildRepository",
]
