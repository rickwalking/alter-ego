"""The write guard every autofix uses: project lock, then lock-version CAS.

Extracted from ``OwnerAutofixService`` (AE-0367/AE-0392) so the AE-0401 slide
fix writes through the very same guard. Under the shared per-project
advisory lock (AE-0316, non-blocking) the caller's ``lock_version`` is bumped
by compare-and-set; a held lock or a moved version raises
``AutofixConflictError`` and nothing is written, so a crashed or concurrent
tick can never apply the same fix twice.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from rag_backend.application.services.carousel.carousel_republish import (
    engine_from_session,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    carousel_project_lock,
)

_T = TypeVar("_T")


class AutofixConflictError(Exception):
    """Another writer holds the lock or moved the lock version."""


@dataclass(frozen=True)
class LockedWrite:
    """The project and the lock version the caller read."""

    project_id: str
    expected_version: int


def lock_engine(db: AsyncSession) -> AsyncEngine:
    """The engine the advisory lock opens its own connection from."""
    bind = db.bind
    if isinstance(bind, AsyncConnection):
        return bind.engine
    return engine_from_session(db)


async def _take_cas(db: AsyncSession, target: LockedWrite) -> None:
    owner = CarouselProjectWriteOwner(db)
    try:
        await owner.bump_resume_lock_version(target.project_id, target.expected_version)
    except ValueError as exc:
        if str(exc) != ERR_VERSION_CONFLICT:
            raise
        raise AutofixConflictError from exc


async def write_locked(
    db: AsyncSession, target: LockedWrite, write: Callable[[], Awaitable[_T]]
) -> _T:
    """Run ``write`` under the project lock after the lock-version CAS."""
    try:
        async with carousel_project_lock(
            lock_engine(db), target.project_id, blocking=False
        ):
            await _take_cas(db, target)
            return await write()
    except CarouselConflictError as exc:
        raise AutofixConflictError from exc


__all__ = ["AutofixConflictError", "LockedWrite", "lock_engine", "write_locked"]
