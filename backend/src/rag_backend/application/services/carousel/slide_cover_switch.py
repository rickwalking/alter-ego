"""Switch a finished carousel's slide 1 to (or off) the GrokBot cover (AE-0418).

The owner's Telegram tap is applied on the worker tick, like "Fix issues":

1. stage the cover file where the slides render (before anything is written,
   so a render never meets a missing file);
2. under the per-project lock, take the lock-version CAS and store
   ``slide_cover`` (a new lock version = a fresh review revision);
3. re-render through the AE-0313 republish path (hero images reused).

A held lock or a moved version is a conflict: nothing is written and the
caller retries on the next tick.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.domain.protocols import CarouselRepository


class CoverRenderer(Protocol):
    """Re-render one carousel; returns the errors that prevented it."""

    async def render(self, project_id: str) -> tuple[str, ...]: ...


class CoverStager(Protocol):
    """Copy the cover file into the project's render tree."""

    async def stage(self, project_id: str, cover: SlideCover) -> bool: ...


@dataclass(frozen=True, kw_only=True)
class SlideCoverSwitchDeps:
    """The session, the carousel repository, the stager and the renderer."""

    db: AsyncSession
    repo: CarouselRepository
    stager: CoverStager
    renderer: CoverRenderer


@dataclass(frozen=True, kw_only=True)
class SlideCoverSwitchCommand:
    """The project, the lock version read, and the cover (None = default)."""

    project_id: str
    expected_version: int
    cover: SlideCover | None


@dataclass(frozen=True, kw_only=True)
class SlideCoverSwitchResult:
    """``AUTOFIX_STATUS_*`` and the render errors, when any."""

    status: str
    render_errors: tuple[str, ...] = ()


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
        errors = await self._deps.renderer.render(command.project_id)
        return SlideCoverSwitchResult(status=AUTOFIX_STATUS_FIXED, render_errors=errors)

    async def _write(self, command: SlideCoverSwitchCommand) -> None:
        project = await self._deps.repo.get_project_by_id(UUID(command.project_id))
        if project is None:
            return
        project.slide_cover = command.cover
        await self._deps.repo.update_project(project)
        await self._deps.db.commit()


__all__ = [
    "CoverRenderer",
    "CoverStager",
    "SlideCoverSwitchCommand",
    "SlideCoverSwitchDeps",
    "SlideCoverSwitchResult",
    "SlideCoverSwitchService",
]
