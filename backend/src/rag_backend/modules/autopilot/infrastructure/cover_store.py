"""SQL store of GrokBot covers (AE-0418, ADR-0024).

Covers are read with their creator asset's artifact-relative path (where the
image is staged for rendering). ``claim_cover`` is a compare-and-set on the
first user, so one cover belongs to one topic. The caller commits.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverClaim,
    ExpiredCoverQuery,
)
from rag_backend.modules.autopilot.infrastructure.cover_models import (
    AutopilotCoverAssetModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware

_Row = tuple[AutopilotCoverAssetModel, str | None]


class SqlCoverAssetStore:
    """Session-scoped adapter for ``autopilot_cover_assets``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_cover(self, cover: CoverAsset) -> None:
        """Insert a freshly uploaded cover."""
        self._session.add(
            AutopilotCoverAssetModel(
                id=cover.asset_id,
                creator_asset_id=str(cover.creator_asset_id),
                kind=cover.kind,
                source_url=cover.source_url,
                width=cover.width,
                height=cover.height,
                created_at=cover.created_at,
            )
        )
        await self._session.flush()

    async def covers_by_ids(self, ids: tuple[UUID, ...]) -> dict[UUID, CoverAsset]:
        """The stored covers among ``ids`` with their staged paths."""
        if not ids:
            return {}
        result = await self._session.execute(
            _with_path().where(AutopilotCoverAssetModel.id.in_(ids))
        )
        covers = (_cover(cast(_Row, tuple(row))) for row in result.all())
        return {cover.asset_id: cover for cover in covers}

    async def claim_cover(self, claim: CoverClaim) -> bool:
        """Set the first user; False when another topic took it first."""
        result = await self._session.execute(
            update(AutopilotCoverAssetModel)
            .where(
                AutopilotCoverAssetModel.id == claim.asset_id,
                AutopilotCoverAssetModel.topic_candidate_id.is_(None),
            )
            .values(topic_candidate_id=claim.topic_candidate_id)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def expired_covers(self, query: ExpiredCoverQuery) -> tuple[CoverAsset, ...]:
        """Unused covers older than the cutoff, oldest first."""
        result = await self._session.execute(
            _with_path()
            .where(
                AutopilotCoverAssetModel.topic_candidate_id.is_(None),
                AutopilotCoverAssetModel.created_at < query.before,
            )
            .order_by(AutopilotCoverAssetModel.created_at)
            .limit(query.limit)
        )
        return tuple(_cover(cast(_Row, tuple(row))) for row in result.all())

    async def delete_covers(self, ids: tuple[UUID, ...]) -> None:
        """Delete the cover rows."""
        if not ids:
            return
        await self._session.execute(
            delete(AutopilotCoverAssetModel).where(AutopilotCoverAssetModel.id.in_(ids))
        )

    async def images_in_use(
        self, creator_asset_ids: tuple[UUID, ...]
    ) -> frozenset[UUID]:
        """The creator assets among the ids that a cover row still references.

        Identical bytes reuse one creator asset, so two covers can share it.
        """
        if not creator_asset_ids:
            return frozenset()
        column = AutopilotCoverAssetModel.creator_asset_id
        result = await self._session.scalars(
            select(column)
            .where(column.in_([str(i) for i in creator_asset_ids]))
            .distinct()
        )
        return frozenset(UUID(value) for value in result.all())

    async def commit(self) -> None:
        """Commit the unit of work."""
        await self._session.commit()


def _with_path() -> Select[tuple[AutopilotCoverAssetModel, str]]:
    return select(
        AutopilotCoverAssetModel, CarouselCreatorAssetModel.relative_path
    ).outerjoin(
        CarouselCreatorAssetModel,
        CarouselCreatorAssetModel.id == AutopilotCoverAssetModel.creator_asset_id,
    )


def _cover(row: _Row) -> CoverAsset:
    model, path = row
    created = aware(model.created_at)
    return CoverAsset(
        asset_id=model.id,
        creator_asset_id=UUID(model.creator_asset_id),
        kind=model.kind,
        source_url=model.source_url,
        width=model.width,
        height=model.height,
        created_at=created if created is not None else model.created_at,
        topic_candidate_id=model.topic_candidate_id,
        staged_path=path or "",
    )


__all__ = ["SqlCoverAssetStore"]
