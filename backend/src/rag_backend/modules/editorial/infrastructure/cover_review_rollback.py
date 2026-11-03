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

``roll_back_cover`` answers whether the rollback settled: the previous cover
restored and rendered again (or the owner's own later value kept). ``False``
(the lock never freed, the row is gone, the re-render failed) is logged as an
error; the needs-republish marker stays, so approval stays refused, and the
caller must not hand the review back to the owner. Every render error,
whatever its type, is a render error here, so the rollback always runs.
"""

from __future__ import annotations

import asyncio
import typing
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_review_switch import (
    LOG_COVER_REVIEW_ROLLBACK_FAILED,
    LOG_COVER_REVIEW_ROLLED_BACK,
    REASON_AUTO_SELECT_NOT_IN_REVIEW,
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
    """Restore the previous cover and render it; True once both settled.

    The restored cover is always rendered again (a failed render may have
    re-rendered part of the slides); a restore that cannot run or a re-render
    that fails is ``False``, and the needs-republish marker stays, so approval
    stays refused until a render settles.
    """
    outcome = await _restore_waiting(session, rollback)
    rerender: tuple[str, ...] = ()
    if outcome == _RESTORED:
        rerender = await render_and_settle(
            session, RenderTarget(project_id=rollback.project_id, in_review=False)
        )
    settled = outcome == _SUPERSEDED or (outcome == _RESTORED and not rerender)
    log = logger.warning if settled else logger.error
    log(
        LOG_COVER_REVIEW_ROLLED_BACK if settled else LOG_COVER_REVIEW_ROLLBACK_FAILED,
        project_id=rollback.project_id,
        outcome=outcome,
        render_errors=list(rollback.render_errors),
        rerender_errors=list(rerender),
    )
    return settled


@dataclass(frozen=True, kw_only=True)
class RenderTarget:
    """The carousel to render; ``in_review`` re-checks the review under the lock."""

    project_id: str
    in_review: bool


async def render_and_settle(
    session: AsyncSession, target: RenderTarget
) -> tuple[str, ...]:
    """Re-render under the build lock; any failure is a render error, never an escape.

    With ``in_review`` the carousel must still wait in final review, unapproved
    and unreleased, when the lock is held, or nothing is rendered. On success
    the needs-republish marker is cleared (the artifacts now carry every pending
    edit, as the picker's republish does). Cancellation is never swallowed.
    """
    from rag_backend.application.services.carousel.carousel_republish import (
        engine_from_session,
        republish_build_lock,
    )
    from rag_backend.domain.models.carousel_conflict import CarouselConflictError
    from rag_backend.modules.editorial.infrastructure import (
        CarouselProjectWriteOwner,
    )

    rendered_from = datetime.now(UTC)
    try:
        async with republish_build_lock(
            engine_from_session(session), target.project_id
        ):
            if target.in_review and not await still_in_review(
                session, target.project_id
            ):
                return (REASON_AUTO_SELECT_NOT_IN_REVIEW,)
            errors = await _finalize(session, target.project_id)
    except CarouselConflictError as exc:
        return (exc.conflict.code,)
    except Exception as exc:
        await session.rollback()
        return (f"{type(exc).__name__}: {exc}",)
    if not errors:
        await CarouselProjectWriteOwner(session).clear_needs_republish(
            target.project_id, rendered_from
        )
    return errors


async def _finalize(session: AsyncSession, project_id: str) -> tuple[str, ...]:
    """The republish pipeline itself (re-render, health check, activation)."""
    from rag_backend.application.services.carousel.editorial_finalize import (
        finalize_carousel_after_images_approval,
    )

    return (await finalize_carousel_after_images_approval(session, project_id)).errors


async def still_in_review(session: AsyncSession, project_id: str) -> bool:
    """No approval, release or run overtook the switch (a fresh locked read)."""
    from rag_backend.application.services.carousel.cover_autoselect import (
        ProjectAtVersion,
    )
    from rag_backend.application.services.carousel.cover_review_switch import (
        render_refusal,
    )

    row = await row_for_update(session, project_id)
    if row is None:
        await session.rollback()
        return False
    found = ProjectAtVersion(
        project=row.to_entity(),
        lock_version=int(row.lock_version or 1),
        workflow_status=str(row.workflow_status or ""),
    )
    await session.rollback()
    return render_refusal(found) is None


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


__all__ = [
    "CoverRollback",
    "RenderTarget",
    "render_and_settle",
    "roll_back_cover",
    "row_for_update",
    "still_in_review",
]
