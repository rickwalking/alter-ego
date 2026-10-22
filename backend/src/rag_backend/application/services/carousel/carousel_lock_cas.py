"""Optimistic ``lock_version`` compare-and-swap shared by the carousel edit services."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner


async def take_lock_version_cas(
    db: AsyncSession, project_id: str, lock_version: int
) -> None:
    """Atomic ``lock_version`` compare-and-swap; a lost race raises 409."""
    try:
        await CarouselProjectWriteOwner(db).bump_resume_lock_version(
            project_id, lock_version
        )
    except ValueError as exc:
        if str(exc) == ERR_VERSION_CONFLICT:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_VERSION_CONFLICT)
            ) from None
        raise
