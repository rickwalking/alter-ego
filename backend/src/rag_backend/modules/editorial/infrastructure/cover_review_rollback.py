"""Undo a website cover switch whose render did not land cleanly.

Called by the review switch store after the re-render when either the render
failed (``slide_cover`` would point at a cover no artifact shows, and a later
republish would ship it unreviewed) or the carousel left the review meanwhile
(an approval landed between the write and the render, so the approved render
must not keep an image the owner never saw). Under the project lock and the
lock-version CAS at the current version, ``slide_cover`` goes back to the value
it had before the switch, only while it is still the switched cover. After an
approval the slides are rendered again from the restored cover. The
needs-republish marker is cleared once the cover and the artifacts agree.
Every rollback logs a warning; a rollback that cannot run (held lock, moved
version, another cover) logs an error and leaves the row alone.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_review_switch import (
    LOG_COVER_REVIEW_ROLLBACK_FAILED,
    LOG_COVER_REVIEW_ROLLED_BACK,
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


@dataclass(frozen=True, kw_only=True)
class CoverRollback:
    """The switched cover, the value before it, and whether to render again."""

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
    """Restore the previous cover; True when it was written."""
    restored = await _restore(session, rollback)
    if not restored:
        logger.error(LOG_COVER_REVIEW_ROLLBACK_FAILED, project_id=rollback.project_id)
        return False
    errors = rollback.render_errors
    if not errors:
        errors = await render_and_settle(session, rollback.project_id)
    else:
        await _clear_marker(session, rollback.project_id)
    logger.warning(
        LOG_COVER_REVIEW_ROLLED_BACK,
        project_id=rollback.project_id,
        render_errors=list(rollback.render_errors),
        rerender_errors=list(errors) if not rollback.render_errors else [],
    )
    return True


async def render_and_settle(session: AsyncSession, project_id: str) -> tuple[str, ...]:
    """The republish render; on success the needs-republish marker is cleared."""
    from rag_backend.modules.editorial.infrastructure.carousel_owner_autofix import (
        RepublishRenderer,
    )

    errors = await RepublishRenderer(session).render(project_id)
    if not errors:
        await _clear_marker(session, project_id)
    return errors


async def _clear_marker(session: AsyncSession, project_id: str) -> None:
    from rag_backend.modules.editorial.infrastructure import (
        CarouselProjectWriteOwner,
    )

    await CarouselProjectWriteOwner(session).clear_needs_republish(project_id)


async def _restore(session: AsyncSession, rollback: CoverRollback) -> bool:
    """The locked write of the previous cover at the version read now."""
    from rag_backend.application.services.carousel.owner_autofix_lock import (
        AutofixConflictError,
        LockedWrite,
        write_locked,
    )

    row = await row_for_update(session, rollback.project_id)
    version = int(row.lock_version or 1) if row is not None else None
    await session.rollback()
    if version is None:
        return False
    target = LockedWrite(project_id=rollback.project_id, expected_version=version)
    try:
        return await write_locked(session, target, lambda: _write(session, rollback))
    except AutofixConflictError:
        return False


async def _write(session: AsyncSession, rollback: CoverRollback) -> bool:
    row = await row_for_update(session, rollback.project_id)
    current = slide_cover_from_row(row.slide_cover) if row is not None else None
    if row is None or current is None or current.asset_id != rollback.switched.asset_id:
        await session.rollback()
        return False
    row.slide_cover = slide_cover_row(rollback.previous)
    await session.commit()
    return True


__all__ = ["CoverRollback", "render_and_settle", "roll_back_cover", "row_for_update"]
