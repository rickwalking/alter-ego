"""Undo a website cover switch whose render did not land cleanly.

Called by the review switch store after the re-render when either the render
failed (``slide_cover`` would point at a cover no artifact shows) or the
carousel left the review meanwhile (an approval landed between the write and
the render, so the approved render must not keep an image the owner never
saw). Under the project lock and the lock-version CAS at the current version,
``slide_cover`` goes back to the value it had before the switch, only while it
is still exactly the switched cover (another value is the owner's own later
choice and is kept). The lock is retried for a bounded time, since a failed
render often means another build still holds it. After an approval the slides
are rendered again from the restored cover.

``roll_back_cover`` answers whether slide 1 no longer carries the switched
cover; ``False`` (the lock never freed, the row is gone) is logged as an error
and the caller must not hand the review back to the owner. Every render error,
whatever its type, is a render error here, so the rollback always runs.
"""

from __future__ import annotations

import asyncio
import typing
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_review_switch import (
    LOG_COVER_REVIEW_ROLLBACK_FAILED,
    LOG_COVER_REVIEW_ROLLED_BACK,
    ROLLBACK_LOCK_ATTEMPTS,
    ROLLBACK_LOCK_RETRY_SECONDS,
)
from rag_backend.domain.models.slide_cover import (
    SlideCover,
    slide_cover_from_row,
    slide_cover_row,
)

if typing.TYPE_CHECKING:
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

logger = structlog.get_logger(__name__)

_RESTORED = "restored"
_SUPERSEDED = "superseded"
_BUSY = "busy"
_GONE = "gone"


@dataclass(frozen=True, kw_only=True)
class CoverRollback:
    """The switched cover, the value before it, and the render's errors."""

    project_id: str
    switched: SlideCover
    previous: SlideCover | None
    render_errors: tuple[str, ...]


async def row_for_update(
    session: AsyncSession, project_id: str
) -> CarouselProjectModel | None:
    """The committed row, locked for this transaction (never the cached one)."""
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel as Row,
    )

    result = await session.execute(
        select(Row)
        .where(Row.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def roll_back_cover(session: AsyncSession, rollback: CoverRollback) -> bool:
    """Restore the previous cover; True once slide 1 no longer carries the switch."""
    outcome = await _restore_waiting(session, rollback)
    if outcome in {_BUSY, _GONE}:
        logger.error(
            LOG_COVER_REVIEW_ROLLBACK_FAILED,
            project_id=rollback.project_id,
            outcome=outcome,
        )
        return False
    rerender: tuple[str, ...] = ()
    if outcome == _RESTORED and not rollback.render_errors:
        rerender = await render_and_settle(session, rollback.project_id)
    logger.warning(
        LOG_COVER_REVIEW_ROLLED_BACK,
        project_id=rollback.project_id,
        outcome=outcome,
        render_errors=list(rollback.render_errors),
        rerender_errors=list(rerender),
    )
    return True


async def render_and_settle(session: AsyncSession, project_id: str) -> tuple[str, ...]:
    """The republish render; any failure is a render error, never an escape.

    On success the needs-republish marker is cleared (the artifacts now carry
    every pending edit, as the picker's republish does).
    """
    from rag_backend.modules.editorial.infrastructure import (
        CarouselProjectWriteOwner,
    )
    from rag_backend.modules.editorial.infrastructure.carousel_owner_autofix import (
        RepublishRenderer,
    )

    try:
        errors = await RepublishRenderer(session).render(project_id)
    except Exception as exc:
        await session.rollback()
        return (f"{type(exc).__name__}: {exc}",)
    if not errors:
        await CarouselProjectWriteOwner(session).clear_needs_republish(project_id)
    return errors


async def _restore_waiting(session: AsyncSession, rollback: CoverRollback) -> str:
    """Try the locked restore until the lock frees, for a bounded time."""
    outcome = _BUSY
    for attempt in range(ROLLBACK_LOCK_ATTEMPTS):
        if attempt:
            await asyncio.sleep(ROLLBACK_LOCK_RETRY_SECONDS)
        outcome = await _restore(session, rollback)
        if outcome != _BUSY:
            return outcome
    return outcome


async def _restore(session: AsyncSession, rollback: CoverRollback) -> str:
    """One locked write of the previous cover at the version read now."""
    from rag_backend.application.services.carousel.owner_autofix_lock import (
        AutofixConflictError,
        LockedWrite,
        write_locked,
    )

    row = await row_for_update(session, rollback.project_id)
    version = int(row.lock_version or 1) if row is not None else None
    await session.rollback()
    if version is None:
        return _GONE
    target = LockedWrite(project_id=rollback.project_id, expected_version=version)
    try:
        return await write_locked(session, target, lambda: _write(session, rollback))
    except AutofixConflictError:
        return _BUSY


async def _write(session: AsyncSession, rollback: CoverRollback) -> str:
    row = await row_for_update(session, rollback.project_id)
    if row is None:
        await session.rollback()
        return _GONE
    if slide_cover_from_row(row.slide_cover) != rollback.switched:
        await session.rollback()
        return _SUPERSEDED
    row.slide_cover = slide_cover_row(rollback.previous)
    await session.commit()
    return _RESTORED


__all__ = ["CoverRollback", "render_and_settle", "roll_back_cover", "row_for_update"]
