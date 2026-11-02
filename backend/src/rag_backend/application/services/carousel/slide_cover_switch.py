"""Switch a finished carousel's slide 1 to (or off) the GrokBot cover.

The owner's Telegram tap is applied on the worker tick, like "Fix issues".
The publish-step picker writes through the same path and may also
bind another library photo as the slide-1 photo (``hook_photo``).

1. stage the cover file where the slides render (before anything is written,
   so a render never meets a missing file);
2. under the per-project lock, take the lock-version CAS and store
   ``slide_cover`` (a new lock version = a fresh review revision), stamping
   the needs-republish marker in the same commit (approval is refused until a
   render settles);
3. re-render through the republish path (hero images reused) and, once it
   succeeded, clear the marker (compare-and-clear: a newer stamp is kept).

A held lock or a moved version is a conflict: nothing is written and the
caller retries on the next tick. With a ``review`` source the write re-reads
the approval under the lock: an approved or published carousel is refused
(``cover_switch_requires_review``), the CAS bump rolled back, nothing rendered.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import (
    ReviewStateSource,
    cover_switch_refusal,
)
from rag_backend.application.services.carousel.owner_autofix_lock import (
    AutofixConflictError,
    LockedWrite,
    write_locked,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.domain.protocols import CarouselRepository


class CoverRenderer(Protocol):
    """Re-render one carousel; returns the errors that prevented it."""

    async def render(self, project_id: str) -> tuple[str, ...]: ...


class RenderMarker(Protocol):
    """The needs-republish marker: stamped with a slide-1 write, cleared after."""

    async def mark(self, project_id: str) -> None:
        """Stamp the marker in the current transaction (the caller commits)."""
        ...

    async def clear(self, project_id: str, rendered_from: datetime) -> None:
        """Clear it unless it was stamped after ``rendered_from``; commit."""
        ...


class CoverStager(Protocol):
    """Copy the cover file into the project's render tree."""

    async def stage(self, project_id: str, cover: SlideCover) -> bool: ...


@dataclass(frozen=True, kw_only=True)
class SlideCoverSwitchDeps:
    """The session, the carousel repository, the stager, the renderer and the
    approval read checked under the lock (None: unchecked)."""

    db: AsyncSession
    repo: CarouselRepository
    stager: CoverStager
    renderer: CoverRenderer
    review: ReviewStateSource | None = None
    marker: RenderMarker | None = None


@dataclass(frozen=True, kw_only=True)
class HookPhotoChoice:
    """A library photo for slide 1, already staged where slides render."""

    asset_id: UUID
    staged_path: str


@dataclass(frozen=True, kw_only=True)
class SlideCoverSwitchCommand:
    """The project, the lock version read, the cover (None = default) and
    the slide-1 library photo to bind (None = keep the bound one)."""

    project_id: str
    expected_version: int
    cover: SlideCover | None
    hook_photo: HookPhotoChoice | None = None


@dataclass(frozen=True, kw_only=True)
class SlideCoverSwitchResult:
    """``AUTOFIX_STATUS_*`` and the render errors, when any."""

    status: str
    render_errors: tuple[str, ...] = ()


class _SwitchRefusedError(Exception):
    """The carousel was approved or released: the locked write must not happen."""


class SlideCoverSwitchService:
    """Stage, store and re-render one slide-1 cover change."""

    def __init__(self, deps: SlideCoverSwitchDeps) -> None:
        self._deps = deps

    async def switch(self, command: SlideCoverSwitchCommand) -> SlideCoverSwitchResult:
        """Apply the change; ``nothing_to_fix`` when the cover file is gone."""
        cover = command.cover
        if cover is not None and not await self._deps.stager.stage(
            command.project_id, cover
        ):
            return SlideCoverSwitchResult(status=AUTOFIX_STATUS_NOTHING_TO_FIX)
        target = LockedWrite(
            project_id=command.project_id, expected_version=command.expected_version
        )
        try:
            await write_locked(self._deps.db, target, lambda: self._write(command))
        except AutofixConflictError:
            return SlideCoverSwitchResult(status=AUTOFIX_STATUS_CONFLICT)
        except _SwitchRefusedError:
            await self._deps.db.rollback()
            return SlideCoverSwitchResult(status=ERR_COVER_SWITCH_REQUIRES_REVIEW)
        rendered_from = datetime.now(UTC)
        errors = await self._deps.renderer.render(command.project_id)
        marker = self._deps.marker
        if marker is not None and not errors:
            await marker.clear(command.project_id, rendered_from)
        return SlideCoverSwitchResult(status=AUTOFIX_STATUS_FIXED, render_errors=errors)

    async def _write(self, command: SlideCoverSwitchCommand) -> None:
        await self._refuse_unreviewed(command.project_id)
        project = await self._deps.repo.get_project_by_id(UUID(command.project_id))
        if project is None:
            return
        project.slide_cover = command.cover
        if command.hook_photo is not None:
            project.hook_asset_id = command.hook_photo.asset_id
            project.hook_asset_staged_path = command.hook_photo.staged_path
        await self._deps.repo.update_project(project)
        if self._deps.marker is not None:
            await self._deps.marker.mark(command.project_id)
        await self._deps.db.commit()

    async def _refuse_unreviewed(self, project_id: str) -> None:
        review = self._deps.review
        if review is None:
            return
        state = await review.review_state(project_id)
        if state is not None and cover_switch_refusal(state) is not None:
            raise _SwitchRefusedError


__all__ = [
    "CoverRenderer",
    "CoverStager",
    "HookPhotoChoice",
    "RenderMarker",
    "SlideCoverSwitchCommand",
    "SlideCoverSwitchDeps",
    "SlideCoverSwitchResult",
    "SlideCoverSwitchService",
]
