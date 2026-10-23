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
    CREATOR_ASSET_ROLE_COVER,
    ERR_CREATOR_ASSET_FORBIDDEN,
    ERR_CREATOR_ASSET_IN_USE,
    ERR_CREATOR_ASSET_NOT_FOUND,
    build_creator_asset_filename,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.carousel_creator_asset import (
    CarouselCreatorAsset,
    CreatorAssetLibraryQuery,
    CreatorAssetTags,
    CreatorAssetUsage,
)
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)


class CreatorAssetInUseError(CreatorAssetValidationError):
    """The photo is still used by ``usages`` (nothing was deleted)."""

    def __init__(self, usages: list[CreatorAssetUsage]) -> None:
        super().__init__(ERR_CREATOR_ASSET_IN_USE)
        self.usages = usages


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


@dataclass(frozen=True)
class LibraryUploadCommand:
    """A photo for the owner's library (no project binding)."""

    user: User
    content: bytes
    declared_mime: str
    role: str | None = None
    pose_tag: str | None = None


@dataclass(frozen=True)
class HookPhotoCommand:
    """Bind a library photo as the project's slide-1 photo."""

    project: CarouselProject
    user: User
    creator_asset_id: UUID
    output_root: Path


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

    async def upload_to_library(
        self, command: LibraryUploadCommand
    ) -> CarouselCreatorAsset:
        """Validate and store a library photo with its role and pose tag."""
        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(
                content=command.content, declared_mime=command.declared_mime
            )
        )
        asset = await self._persist_normalized_asset(
            owner_id=str(command.user.id), normalized=normalized
        )
        tagged = await self._asset_repo.set_tags(
            CreatorAssetTags(
                asset_id=asset.id, role=command.role, pose_tag=command.pose_tag
            )
        )
        return tagged or asset

    async def list_library(
        self, user: User, role: str | None
    ) -> list[CarouselCreatorAsset]:
        """The caller's own photos, newest first (admins see their own too)."""
        return await self._asset_repo.list_for_owner(
            CreatorAssetLibraryQuery(owner_id=str(user.id), role=role)
        )

    async def library_image_path(self, user: User, asset_id: UUID) -> Path:
        """The stored WebP of one of the caller's photos."""
        asset = await self._asset_repo.get_by_id(asset_id)
        if asset is None:
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_NOT_FOUND)
        if not user.is_admin() and asset.owner_id != str(user.id):
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_FORBIDDEN)
        path = self._canonical_storage_path(asset.content_sha256)
        if not path.is_file():
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_NOT_FOUND)
        return path

    async def delete_library_photo(self, user: User, asset_id: UUID) -> Path | None:
        """Delete one of the caller's photos (owner only); the file to remove.

        Raises not-found for an unknown id, forbidden for anyone but the owner
        (admins included: the library is the owner's personal data) and
        :class:`CreatorAssetInUseError` while any carousel uses the photo. The
        row delete is flushed, not committed: the caller commits, then removes
        the returned WebP (None while another row points at the same bytes or
        when it is already gone).
        """
        asset = await self._asset_repo.get_by_id(asset_id)
        if asset is None:
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_NOT_FOUND)
        if asset.owner_id != str(user.id):
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_FORBIDDEN)
        usages = await self._asset_repo.projects_using(asset_id)
        if usages:
            raise CreatorAssetInUseError(usages)
        path = self.stored_file(asset)
        remaining = await self._asset_repo.delete(asset)
        return path if remaining == 0 else None

    def has_stored_file(self, asset: CarouselCreatorAsset) -> bool:
        """True when the asset's canonical WebP exists (PR #106 review)."""
        try:
            return self._canonical_storage_path(asset.content_sha256).is_file()
        except CreatorAssetValidationError:
            return False

    def stored_file(self, asset: CarouselCreatorAsset) -> Path | None:
        """The asset's canonical WebP, or None when it is gone."""
        if not self.has_stored_file(asset):
            return None
        return self._canonical_storage_path(asset.content_sha256)

    async def store_cover(
        self, owner_id: str, normalized: NormalizedCreatorAsset
    ) -> CarouselCreatorAsset:
        """Store a validated GrokBot cover with role ``cover``.

        Bytes the owner already has as a library photo reuse that row and keep
        its role (the owner's photo is never re-tagged).
        """
        existing = await self._asset_repo.get_by_owner_and_content_sha256(
            owner_id, normalized.content_sha256
        )
        asset = await self._persist_normalized_asset(owner_id, normalized)
        if existing is not None:
            return asset
        tagged = await self._asset_repo.set_tags(
            CreatorAssetTags(asset_id=asset.id, role=CREATOR_ASSET_ROLE_COVER)
        )
        return tagged or asset

    async def select_hook_photo(self, command: HookPhotoCommand) -> CarouselProject:
        """Bind the slide-1 photo and stage it where the slides are rendered."""
        self._assert_owner_or_admin(command.project, command.user)
        asset = await self._asset_repo.get_by_id(command.creator_asset_id)
        if asset is None:
            raise CreatorAssetValidationError(ERR_CREATOR_ASSET_NOT_FOUND)
        self._assert_asset_access(asset, command.project, command.user)
        command.project.hook_asset_id = asset.id
        command.project.hook_asset_staged_path = asset.relative_path
        updated = await self._carousel_repo.update_project(command.project)
        self.stage_into_candidate_artifact(
            StageCreatorAssetCommand(asset=asset, staging_root=command.output_root)
        )
        return updated

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
    "CreatorAssetInUseError",
    "CreatorAssetSelectCommand",
    "CreatorAssetService",
    "CreatorAssetUploadCommand",
    "StageCreatorAssetCommand",
    "StagedCreatorAssetPaths",
]
