"""Postgres store of slide-1 cover generations (the Grok budget log).

Owned by the editorial module (its own unit of work: ``commit``).

``lock_owner`` takes the owner's user row ``FOR UPDATE`` so the cap check
and the insert of one generation are serialised per owner (a no-op on
SQLite). Settling is conditional on the row still being ``pending``.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_generation import FAILURE_INTERRUPTED
from rag_backend.domain.models.cover_generation import (
    CoverGeneration,
    CoverGenerationOutcome,
    CoverGenerationStatus,
)
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.models.carousel_cover_generation import (
    CarouselCoverGenerationModel,
)

_PENDING = CoverGenerationStatus.PENDING.value
_FAILED = CoverGenerationStatus.FAILED.value
_SUCCEEDED = CoverGenerationStatus.SUCCEEDED.value
_Row = CarouselCoverGenerationModel


class SqlCoverGenerationRepository:
    """Cover generation rows of one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_owner(self, owner_id: str) -> None:
        """Serialise the owner's generations until the transaction ends."""
        await self._session.execute(
            select(UserModel.id).where(UserModel.id == owner_id).with_for_update()
        )

    async def create(self, generation: CoverGeneration) -> None:
        """Insert a new generation (flushed, not committed)."""
        self._session.add(_Row.from_entity(generation))
        await self._session.flush()

    async def for_project(self, project_id: str) -> tuple[CoverGeneration, ...]:
        """The carousel's generations, newest first."""
        rows = await self._session.scalars(
            select(_Row)
            .where(_Row.project_id == project_id)
            .order_by(_Row.created_at.desc(), _Row.id)
        )
        return tuple(row.to_entity() for row in rows)

    async def count_owner_since(self, owner_id: str, since: datetime) -> int:
        """The owner's pending and succeeded generations since ``since``."""
        count = await self._session.scalar(
            select(func.count())
            .select_from(_Row)
            .where(
                _Row.owner_id == owner_id,
                _Row.status != _FAILED,
                _Row.created_at >= since,
            )
        )
        return int(count or 0)

    async def settle(self, outcome: CoverGenerationOutcome) -> bool:
        """Mark a pending generation succeeded or failed; False when not pending."""
        status = _FAILED if outcome.error_code else _SUCCEEDED
        result = await self._session.execute(
            update(_Row)
            .where(_Row.id == str(outcome.generation_id), _Row.status == _PENDING)
            .values(
                status=status,
                completed_at=outcome.at,
                error_code=outcome.error_code,
                result_asset_id=(
                    str(outcome.result_asset_id) if outcome.result_asset_id else None
                ),
            )
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def fail_stale(self, created_before: datetime, at: datetime) -> int:
        """Fail pending generations created before the cutoff (a lost run)."""
        result = await self._session.execute(
            update(_Row)
            .where(_Row.status == _PENDING, _Row.created_at < created_before)
            .values(status=_FAILED, completed_at=at, error_code=FAILURE_INTERRUPTED)
        )
        return int(cast(CursorResult[object], result).rowcount or 0)

    async def get(self, generation_id: UUID) -> CoverGeneration | None:
        """One generation, or None."""
        row = await self._session.get(_Row, str(generation_id))
        return row.to_entity() if row is not None else None

    async def commit(self) -> None:
        """Commit the session."""
        await self._session.commit()

    async def rollback(self) -> None:
        """End the session's transaction without writing (releases the connection)."""
        await self._session.rollback()


__all__ = ["SqlCoverGenerationRepository"]
