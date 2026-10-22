"""Save a carousel's Instagram caption and LinkedIn posts.

The publish page edits the caption and the PT/EN LinkedIn posts. A save:

1. Refuses while a workflow run is active (the run writes the same row).
2. Takes the ``lock_version`` compare-and-swap with the version the page loaded,
   so a save prepared against an older state gets the typed ``version_conflict``.
3. Writes the texts through the carousel repository, whose ``update_project``
   lands them in the canonical ``blog_posts.distribution`` home and its embedded
   mirror (ADR-011) in the same transaction.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_lock_cas import (
    take_lock_version_cas,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_copy_edit import LOG_EVENT_COPY_SAVED
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.domain.protocols.repositories import CarouselRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CopyEdits:
    """The texts to save; ``None`` keeps the saved text."""

    caption: str | None = None
    linkedin_post_pt: str | None = None
    linkedin_post_en: str | None = None


@dataclass(frozen=True)
class CopyEditCommand:
    """One save of ``edits`` on ``project`` against the loaded ``lock_version``."""

    project: CarouselProject
    lock_version: int
    edits: CopyEdits


@dataclass(frozen=True)
class CopyEditResult:
    """The saved project and the lock version the next save must send."""

    project: CarouselProject
    lock_version: int


@dataclass(frozen=True)
class CarouselCopyEditDeps:
    """Collaborators sharing one request session."""

    db: AsyncSession
    repo: CarouselRepository


class CarouselCopyEditService:
    """Saves caption and LinkedIn post edits under the ``lock_version`` CAS."""

    def __init__(self, deps: CarouselCopyEditDeps) -> None:
        self._db = deps.db
        self._repo = deps.repo

    async def save(self, command: CopyEditCommand) -> CopyEditResult:
        """Check the run guard and the lock, apply the edits and commit."""
        project = command.project
        if project.phase_status == PHASE_STATUS_IN_PROGRESS:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
            )
        await take_lock_version_cas(self._db, str(project.id), command.lock_version)
        _apply(project, command.edits)
        saved = await self._repo.update_project(project)
        logger.info(
            LOG_EVENT_COPY_SAVED,
            project_id=str(project.id),
            caption=command.edits.caption is not None,
            linkedin_post_pt=command.edits.linkedin_post_pt is not None,
            linkedin_post_en=command.edits.linkedin_post_en is not None,
        )
        return CopyEditResult(project=saved, lock_version=command.lock_version + 1)


def _apply(project: CarouselProject, edits: CopyEdits) -> None:
    """Copy each sent text onto the project; unsent texts stay as saved."""
    if edits.caption is not None:
        project.caption = edits.caption
    if edits.linkedin_post_pt is not None:
        project.linkedin_post_pt = edits.linkedin_post_pt
    if edits.linkedin_post_en is not None:
        project.linkedin_post_en = edits.linkedin_post_en


__all__ = [
    "CarouselCopyEditDeps",
    "CarouselCopyEditService",
    "CopyEditCommand",
    "CopyEditResult",
    "CopyEdits",
]
