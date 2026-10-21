"""The GrokBot slide-1 cover seam the autopilot drives in-process (AE-0418).

- ``store_cover_image``: validate a cover upload and store it as a creator
  asset with role ``cover`` (raises ``CoverAssetError`` with the contract code);
- ``cover_image_file``: the stored WebP of a cover (Telegram preview);
- ``delete_cover_images``: the sweep of unused, expired covers;
- ``stage_slide_cover``: copy the cover where a project's slides render;
- ``switch_slide_cover``: store the owner's choice on a finished carousel and
  re-render it through the republish path.

The ORM, repositories and the carousel services are imported lazily (the
editorial facade loads while the ORM registry is still initialising).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_ROLE_COVER
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.editorial.domain.models import CarouselProject
from rag_backend.modules.editorial.infrastructure.pov_inputs import (
    creator_asset_service,
    creator_assets,
    project_output_root,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.slide_cover_switch import (
        SlideCoverSwitchResult,
        SlideCoverSwitchService,
    )


@dataclass(frozen=True, kw_only=True)
class CoverImageRequest:
    """One upload: the bytes, its kind and the user that owns the asset."""

    session: AsyncSession
    owner_id: str
    content: bytes
    kind: str


@dataclass(frozen=True, kw_only=True)
class StoredCoverImage:
    """The creator asset a cover was stored as, and its final size."""

    creator_asset_id: UUID
    width: int
    height: int


@dataclass(frozen=True, kw_only=True)
class CoverSwitchRequest:
    """A finished carousel, the lock version read, and the cover to show."""

    session: AsyncSession
    project_id: str
    expected_version: int
    cover: SlideCover | None


async def store_cover_image(request: CoverImageRequest) -> StoredCoverImage:
    """Validate, re-encode and store; raises ``CoverAssetError``."""
    from rag_backend.application.services.carousel.cover_asset_validation import (
        CoverImageUpload,
        validate_cover_image,
    )

    normalized = validate_cover_image(
        CoverImageUpload(content=request.content, kind=request.kind)
    )
    service = creator_asset_service(request.session)
    asset = await service.store_cover(request.owner_id, normalized)
    return StoredCoverImage(
        creator_asset_id=asset.id, width=normalized.width, height=normalized.height
    )


async def cover_image_file(session: AsyncSession, asset_id: UUID) -> Path | None:
    """The stored WebP of a creator asset, or None when it is gone."""
    asset = await creator_assets(session).get_by_id(asset_id)
    if asset is None:
        return None
    return creator_asset_service(session).stored_file(asset)


async def delete_cover_images(
    session: AsyncSession, asset_ids: tuple[UUID, ...]
) -> int:
    """Delete cover-role creator assets and their files (flush, no commit).

    A row with another role (an owner photo whose bytes Grok re-sent) is kept,
    so is a row a project still renders (``hook_asset_id`` or ``slide_cover``),
    and a file is kept while another row still points at the same bytes.
    """
    deleted = 0
    for asset_id in asset_ids:
        asset = await creator_assets(session).get_by_id(asset_id)
        if asset is None or asset.role != CREATOR_ASSET_ROLE_COVER:
            continue
        if await _used_by_a_project(session, asset_id):
            continue
        await _delete_row(session, asset)
        deleted += 1
    return deleted


async def _used_by_a_project(session: AsyncSession, asset_id: UUID) -> bool:
    """True when a carousel's slide 1 points at the creator asset."""
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    key = str(asset_id)
    found = await session.scalar(
        select(CarouselProjectModel.id)
        .where(
            or_(
                CarouselProjectModel.hook_asset_id == key,
                cast(CarouselProjectModel.slide_cover, String).contains(key),
            )
        )
        .limit(1)
    )
    return found is not None


async def _delete_row(session: AsyncSession, asset: CarouselCreatorAsset) -> None:
    from rag_backend.infrastructure.database.models.carousel_creator_asset import (
        CarouselCreatorAssetModel,
    )

    model = await session.get(CarouselCreatorAssetModel, str(asset.id))
    if model is None:
        return
    path = creator_asset_service(session).stored_file(asset)
    await session.delete(model)
    await session.flush()
    count = await session.scalar(
        select(func.count(CarouselCreatorAssetModel.id)).where(
            CarouselCreatorAssetModel.content_sha256 == asset.content_sha256
        )
    )
    if path is not None and not count:
        path.unlink(missing_ok=True)


async def stage_slide_cover(session: AsyncSession, project: CarouselProject) -> bool:
    """Copy the project's chosen cover where its slides render.

    False when the project has no cover or its stored file is gone.
    """
    cover = project.slide_cover
    if cover is None:
        return False
    from rag_backend.application.services.carousel.creator_asset_service import (
        StageCreatorAssetCommand,
    )

    service = creator_asset_service(session)
    asset = await creator_assets(session).get_by_id(cover.asset_id)
    if asset is None or not service.has_stored_file(asset):
        return False
    service.stage_into_candidate_artifact(
        StageCreatorAssetCommand(asset=asset, staging_root=project_output_root(project))
    )
    return True


class _ProjectStager:
    """Stage a cover into the render tree of a project read by id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def stage(self, project_id: str, cover: SlideCover) -> bool:
        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )

        repo = PostgresCarouselRepository(session=self._session)
        project = await repo.get_project_by_id(UUID(project_id))
        if project is None:
            return False
        project.slide_cover = cover
        return await stage_slide_cover(self._session, project)


def slide_cover_switch_service(session: AsyncSession) -> SlideCoverSwitchService:
    """The cover switch of one session: project stager + republish renderer."""
    from rag_backend.application.services.carousel.slide_cover_switch import (
        SlideCoverSwitchDeps,
        SlideCoverSwitchService,
    )
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.modules.editorial.infrastructure.carousel_owner_autofix import (
        RepublishRenderer,
    )

    return SlideCoverSwitchService(
        SlideCoverSwitchDeps(
            db=session,
            repo=PostgresCarouselRepository(session=session),
            stager=_ProjectStager(session),
            renderer=RepublishRenderer(session),
        )
    )


async def switch_slide_cover(request: CoverSwitchRequest) -> SlideCoverSwitchResult:
    """Stage, store and re-render one slide-1 cover change."""
    from rag_backend.application.services.carousel.slide_cover_switch import (
        SlideCoverSwitchCommand,
    )

    service = slide_cover_switch_service(request.session)
    return await service.switch(
        SlideCoverSwitchCommand(
            project_id=request.project_id,
            expected_version=request.expected_version,
            cover=request.cover,
        )
    )


__all__ = [
    "CoverImageRequest",
    "CoverSwitchRequest",
    "StoredCoverImage",
    "cover_image_file",
    "delete_cover_images",
    "slide_cover_switch_service",
    "stage_slide_cover",
    "store_cover_image",
    "switch_slide_cover",
]
