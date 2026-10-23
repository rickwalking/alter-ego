"""PostgreSQL repository for managed carousel creator assets."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_ROLE_COVER
from rag_backend.domain.models.carousel_creator_asset import (
    CarouselCreatorAsset,
    CreatorAssetLibraryQuery,
    CreatorAssetTags,
    CreatorAssetTopicUsage,
    CreatorAssetUsage,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
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

    async def get_for_update(self, asset_id: UUID) -> CarouselCreatorAsset | None:
        """The asset with its row locked until commit.

        A carousel that starts referencing the asset takes a key-share lock on
        the row, so it waits for this transaction instead of losing the
        reference to the delete.
        """
        stmt = (
            select(CarouselCreatorAssetModel)
            .where(CarouselCreatorAssetModel.id == str(asset_id))
            .with_for_update()
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return model.to_entity() if model is not None else None

    async def topics_using(self, asset_id: UUID) -> tuple[CreatorAssetTopicUsage, ...]:
        """The autopilot cover rows that use the asset (pending topics included)."""
        from rag_backend.modules.autopilot.public import cover_topics_using

        return await cover_topics_using(self._session, asset_id)

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

    async def projects_using(self, asset_id: UUID) -> list[CreatorAssetUsage]:
        """The carousels that use the asset: creator asset, hook photo or cover."""
        key = str(asset_id)
        project = CarouselProjectModel
        stmt = (
            select(project.id, project.title)
            .where(
                or_(
                    project.creator_asset_id == key,
                    project.hook_asset_id == key,
                    cast(project.slide_cover, String).contains(key),
                )
            )
            .order_by(project.created_at.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            CreatorAssetUsage(project_id=UUID(str(row.id)), title=row.title)
            for row in rows
        ]

    async def delete(self, asset: CarouselCreatorAsset) -> int:
        """Delete the row (flush, the caller commits); rows left with the same bytes."""
        await self._session.execute(
            delete(CarouselCreatorAssetModel).where(
                CarouselCreatorAssetModel.id == str(asset.id)
            )
        )
        await self._session.flush()
        remaining = await self._session.scalar(
            select(func.count(CarouselCreatorAssetModel.id)).where(
                CarouselCreatorAssetModel.content_sha256 == asset.content_sha256
            )
        )
        return int(remaining or 0)

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
