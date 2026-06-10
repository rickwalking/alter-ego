"""PostgreSQL repository for managed carousel creator assets."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
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
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()
