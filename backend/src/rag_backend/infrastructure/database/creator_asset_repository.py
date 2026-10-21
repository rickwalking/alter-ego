"""PostgreSQL repository for managed carousel creator assets."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_ROLE_COVER
from rag_backend.domain.models.carousel_creator_asset import (
    CarouselCreatorAsset,
    CreatorAssetLibraryQuery,
    CreatorAssetTags,
)
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)

_ERR_ASSET_NOT_FOUND = "Creator asset {} not found"


class PostgresCreatorAssetRepository:
    """PostgreSQL persistence for carousel creator assets."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, asset_id: UUID) -> CarouselCreatorAsset | None:
        model = await self._session.get(CarouselCreatorAssetModel, str(asset_id))
        if model is None:
            return None
        return model.to_entity()

    async def get_by_owner_and_content_sha256(
        self,
        owner_id: str,
        content_sha256: str,
    ) -> CarouselCreatorAsset | None:
        stmt = select(CarouselCreatorAssetModel).where(
            CarouselCreatorAssetModel.owner_id == owner_id,
            CarouselCreatorAssetModel.content_sha256 == content_sha256,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model is not None else None

    async def create(self, asset: CarouselCreatorAsset) -> CarouselCreatorAsset:
        model = CarouselCreatorAssetModel.from_entity(asset)
        self._session.add(model)
        await self._session.flush()
        return await self._save(model)

    async def _save(self, model: CarouselCreatorAssetModel) -> CarouselCreatorAsset:
        """The single commit point of this adapter (create and tag updates)."""
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()

    async def list_for_owner(
        self, query: CreatorAssetLibraryQuery
    ) -> list[CarouselCreatorAsset]:
        """The owner's photo library, newest first, optionally by role.

        GrokBot covers (role ``cover``) are not library photos; they
        are listed only when asked for by that role.
        """
        role = CarouselCreatorAssetModel.role
        stmt = select(CarouselCreatorAssetModel).where(
            CarouselCreatorAssetModel.owner_id == query.owner_id
        )
        if query.role is not None:
            stmt = stmt.where(role == query.role)
        else:
            stmt = stmt.where(or_(role.is_(None), role != CREATOR_ASSET_ROLE_COVER))
        stmt = stmt.order_by(CarouselCreatorAssetModel.created_at.desc()).limit(
            query.limit
        )
        result = await self._session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def set_tags(self, tags: CreatorAssetTags) -> CarouselCreatorAsset | None:
        """Set an asset's library role and pose tag."""
        model = await self._session.get(CarouselCreatorAssetModel, str(tags.asset_id))
        if model is None:
            return None
        model.role = tags.role
        model.pose_tag = tags.pose_tag
        return await self._save(model)
