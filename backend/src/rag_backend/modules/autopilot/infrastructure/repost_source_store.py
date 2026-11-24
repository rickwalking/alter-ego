"""SQL store of repost source videos. The caller commits."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.repost_source import (
    RepostSource,
    VideoProbe,
)
from rag_backend.modules.autopilot.infrastructure.repost_source_models import (
    RepostSourceModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware
from rag_backend.modules.autopilot.repost_source_constants import SOURCE_SWEEP_LIMIT

_S = RepostSourceModel


class SqlRepostSourceStore:
    """``RepostSourceStore`` on one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, source: RepostSource) -> None:
        """Add the row."""
        probe = source.probe
        self._session.add(
            _S(
                id=source.id,
                file_name=source.file_name,
                size_bytes=source.size_bytes,
                codec=probe.codec,
                width=probe.width,
                height=probe.height,
                duration_s=probe.duration_s,
                repost_id=source.repost_id,
                created_at=source.created_at,
            )
        )

    async def get(self, asset_id: UUID) -> RepostSource | None:
        """One upload."""
        row = await self._session.get(_S, asset_id)
        return None if row is None else _to_source(row)

    async def for_repost(self, repost_id: UUID) -> RepostSource | None:
        """The upload a draft uses, if any."""
        row = await self._session.scalar(select(_S).where(_S.repost_id == repost_id))
        return None if row is None else _to_source(row)

    async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
        """Mark an unused upload as the draft's; False when it is taken."""
        result = await self._session.execute(
            update(_S)
            .where(_S.id == asset_id, _S.repost_id.is_(None))
            .values(repost_id=repost_id)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def unused_before(self, before: datetime) -> tuple[RepostSource, ...]:
        """Unused uploads created before ``before``, oldest first."""
        rows = await self._session.scalars(
            select(_S)
            .where(_S.repost_id.is_(None), _S.created_at < before)
            .order_by(_S.created_at)
            .limit(SOURCE_SWEEP_LIMIT)
        )
        return tuple(_to_source(row) for row in rows)

    async def delete(self, asset_id: UUID) -> None:
        """Drop the row."""
        await self._session.execute(delete(_S).where(_S.id == asset_id))

    async def commit(self) -> None:
        """Commit the session."""
        await self._session.commit()


def _to_source(row: RepostSourceModel) -> RepostSource:
    return RepostSource(
        id=row.id,
        file_name=row.file_name,
        size_bytes=row.size_bytes,
        probe=VideoProbe(
            codec=row.codec,
            width=row.width,
            height=row.height,
            duration_s=row.duration_s,
        ),
        created_at=aware(row.created_at) or row.created_at,
        repost_id=row.repost_id,
    )


__all__ = ["SqlRepostSourceStore"]
