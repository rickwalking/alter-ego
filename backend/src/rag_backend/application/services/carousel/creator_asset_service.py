"""Service for managed carousel creator branding assets."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetUpload,
    CreatorAssetValidationError,
    NormalizedCreatorAsset,
    validate_and_normalize_creator_asset,
)
from rag_backend.domain.constants.creator_asset import (
    ERR_CREATOR_ASSET_FORBIDDEN,
    ERR_CREATOR_ASSET_NOT_FOUND,
    build_creator_asset_filename,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)


@dataclass(frozen=True)
class StageCreatorAssetCommand:
    asset: CarouselCreatorAsset
    staging_root: Path


@dataclass(frozen=True)
class StagedCreatorAssetPaths:
    relative_path: str
    standard_relative_path: str
    hd_relative_path: str


@dataclass(frozen=True)
class CreatorAssetUploadCommand:
    project: CarouselProject
    user: User
    content: bytes
    declared_mime: str


@dataclass(frozen=True)
class CreatorAssetSelectCommand:
    project: CarouselProject
    user: User
    creator_asset_id: UUID


class CreatorAssetService:
    """Upload, select, and stage managed creator branding assets."""

    def __init__(
        self,
        asset_repo: PostgresCreatorAssetRepository,
        carousel_repo: CarouselRepository,
        assets_root: Path,
    ) -> None:
        self._asset_repo = asset_repo
        self._carousel_repo = carousel_repo
        self._assets_root = assets_root.resolve()

    async def upload_for_project(
        self,
        command: CreatorAssetUploadCommand,
    ) -> tuple[CarouselCreatorAsset, CarouselProject]:
        """Validate upload, persist asset, and bind it to the project."""
        self._assert_owner_or_admin(command.project, command.user)
        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(
                content=command.content,
                declared_mime=command.declared_mime,
            )
        )
        asset = await self._persist_normalized_asset(
            owner_id=str(command.project.owner_id or command.user.id),
            normalized=normalized,
        )
        updated = await self._bind_asset_to_project(command.project, asset)
        self._stage_into_output_dir(updated, asset)
        return asset, updated

    async def select_for_project(
        self,
        command: CreatorAssetSelectCommand,
    ) -> tuple[CarouselCreatorAsset, CarouselProject]:
        """Bind an existing managed asset to a carousel project."""
        self._assert_owner_or_admin(command.project, command.user)
        asset = await self._asset_repo.get_by_id(command.creator_asset_id)
        if asset is None:
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_NOT_FOUND)
        self._assert_asset_access(asset, command.project, command.user)
        updated = await self._bind_asset_to_project(command.project, asset)
        self._stage_into_output_dir(updated, asset)
        return asset, updated

    def stage_into_candidate_artifact(
        self,
        command: StageCreatorAssetCommand,
    ) -> StagedCreatorAssetPaths:
        """Copy a managed asset into a candidate artifact staging tree."""
        source = self._canonical_storage_path(command.asset.content_sha256)
        if not source.is_file():
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_NOT_FOUND)
        destination = command.staging_root / command.asset.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        relative = command.asset.relative_path
        return StagedCreatorAssetPaths(
            relative_path=relative,
            standard_relative_path=relative,
            hd_relative_path=relative,
        )

    async def _persist_normalized_asset(
        self,
        owner_id: str,
        normalized: NormalizedCreatorAsset,
    ) -> CarouselCreatorAsset:
        existing = await self._asset_repo.get_by_owner_and_content_sha256(
            owner_id,
            normalized.content_sha256,
        )
        self._write_canonical_file(normalized)
        if existing is not None and existing.owner_id == owner_id:
            return existing
        asset = CarouselCreatorAsset(
            owner_id=owner_id,
            content_sha256=normalized.content_sha256,
            media_type=normalized.media_type,
            width=normalized.width,
            height=normalized.height,
            relative_path=normalized.relative_path,
        )
        return await self._asset_repo.create(asset)

    def _write_canonical_file(self, normalized: NormalizedCreatorAsset) -> Path:
        destination = self._canonical_storage_path(normalized.content_sha256)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file():
            destination.write_bytes(normalized.webp_bytes)
        if not destination.is_relative_to(self._assets_root):
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_FORBIDDEN)
        return destination

    def _canonical_storage_path(self, content_sha256: str) -> Path:
        path = self._assets_root / build_creator_asset_filename(content_sha256)
        if not path.resolve().is_relative_to(self._assets_root):
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_FORBIDDEN)
        return path

    async def _bind_asset_to_project(
        self,
        project: CarouselProject,
        asset: CarouselCreatorAsset,
    ) -> CarouselProject:
        project.creator_asset_id = asset.id
        project.creator_asset_staged_path = asset.relative_path
        return await self._carousel_repo.update_project(project)

    def _stage_into_output_dir(
        self,
        project: CarouselProject,
        asset: CarouselCreatorAsset,
    ) -> None:
        if not project.output_dir:
            return
        output_root = Path(project.output_dir).resolve()
        self.stage_into_candidate_artifact(
            StageCreatorAssetCommand(asset=asset, staging_root=output_root)
        )

    @staticmethod
    def _assert_owner_or_admin(project: CarouselProject, user: User) -> None:
        if user.is_admin():
            return
        owner_id = project.owner_id
        if owner_id is None or str(user.id) != owner_id:
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_FORBIDDEN)

    @staticmethod
    def _assert_asset_access(
        asset: CarouselCreatorAsset,
        project: CarouselProject,
        user: User,
    ) -> None:
        if user.is_admin():
            return
        if asset.owner_id == str(user.id):
            return
        if project.owner_id is not None and asset.owner_id == project.owner_id:
            return
        raise CreatorAssetValidationError(ERR_CREATOR_ASSET_FORBIDDEN)


__all__ = [
    "CreatorAssetSelectCommand",
    "CreatorAssetService",
    "CreatorAssetUploadCommand",
    "StageCreatorAssetCommand",
    "StagedCreatorAssetPaths",
]
