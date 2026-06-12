"""Unit tests for per-owner creator asset deduplication.

Feature: Versioned carousel presentation contract
Scenario: Re-uploading identical content dedupes per owner
Scenario: Identical content from different owners stays isolated
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetService,
    CreatorAssetUploadCommand,
)
from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_MIME_PNG
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)


def _make_png_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color="green").save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeAssetRepo:
    def __init__(self) -> None:
        self.assets: list[CarouselCreatorAsset] = []
        self.create_calls = 0

    async def get_by_id(self, asset_id: UUID) -> CarouselCreatorAsset | None:
        return next((asset for asset in self.assets if asset.id == asset_id), None)

    async def get_by_owner_and_content_sha256(
        self,
        owner_id: str,
        content_sha256: str,
    ) -> CarouselCreatorAsset | None:
        return next(
            (
                asset
                for asset in self.assets
                if asset.owner_id == owner_id and asset.content_sha256 == content_sha256
            ),
            None,
        )

    async def create(self, asset: CarouselCreatorAsset) -> CarouselCreatorAsset:
        self.create_calls += 1
        self.assets.append(asset)
        return asset


class _FakeCarouselRepo:
    async def update_project(self, project: CarouselProject) -> CarouselProject:
        return project


def _make_project(owner_id: str) -> CarouselProject:
    return CarouselProject(
        topic="topic",
        audience="audience",
        niche="niche",
        owner_id=owner_id,
    )


def _make_user(user_id: UUID) -> User:
    return User(
        email="creator@example.com",
        full_name="Creator",
        hashed_password="hash",
        id=user_id,
    )


def _make_service(
    asset_repo: _FakeAssetRepo,
    assets_root: Path,
) -> CreatorAssetService:
    return CreatorAssetService(
        asset_repo=cast(PostgresCreatorAssetRepository, asset_repo),
        carousel_repo=cast(CarouselRepository, _FakeCarouselRepo()),
        assets_root=assets_root,
    )


def _upload_command(owner_id: str, content: bytes) -> CreatorAssetUploadCommand:
    user_id = UUID(owner_id)
    return CreatorAssetUploadCommand(
        project=_make_project(owner_id),
        user=_make_user(user_id),
        content=content,
        declared_mime=CREATOR_ASSET_MIME_PNG,
    )


@pytest.mark.unit
class TestCreatorAssetPerOwnerDedup:
    @pytest.mark.asyncio
    async def test_same_owner_reupload_returns_existing_asset(
        self, tmp_path: Path
    ) -> None:
        """Re-uploading identical content for one owner must not create a new row."""
        asset_repo = _FakeAssetRepo()
        service = _make_service(asset_repo, tmp_path)
        owner_id = str(uuid4())
        content = _make_png_bytes()

        first_asset, _ = await service.upload_for_project(
            _upload_command(owner_id, content)
        )
        second_asset, _ = await service.upload_for_project(
            _upload_command(owner_id, content)
        )

        assert second_asset.id == first_asset.id
        assert asset_repo.create_calls == 1
        assert len(asset_repo.assets) == 1

    @pytest.mark.asyncio
    async def test_different_owners_get_distinct_assets_for_same_content(
        self,
        tmp_path: Path,
    ) -> None:
        """Identical bytes from two owners must produce two owner-scoped rows."""
        asset_repo = _FakeAssetRepo()
        service = _make_service(asset_repo, tmp_path)
        owner_a = str(uuid4())
        owner_b = str(uuid4())
        content = _make_png_bytes()

        asset_a, _ = await service.upload_for_project(_upload_command(owner_a, content))
        asset_b, _ = await service.upload_for_project(_upload_command(owner_b, content))

        assert asset_a.id != asset_b.id
        assert asset_a.content_sha256 == asset_b.content_sha256
        assert asset_a.owner_id == owner_a
        assert asset_b.owner_id == owner_b
        assert asset_repo.create_calls == 2

    @pytest.mark.asyncio
    async def test_canonical_file_is_shared_across_owners(self, tmp_path: Path) -> None:
        """Content-addressed storage keeps one canonical file per content hash."""
        asset_repo = _FakeAssetRepo()
        service = _make_service(asset_repo, tmp_path)
        content = _make_png_bytes()

        await service.upload_for_project(_upload_command(str(uuid4()), content))
        await service.upload_for_project(_upload_command(str(uuid4()), content))

        stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]
        assert len(stored_files) == 1
