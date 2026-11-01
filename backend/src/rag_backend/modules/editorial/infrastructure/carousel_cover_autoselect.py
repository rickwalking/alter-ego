"""The editorial side of using an autopilot-generated cover on slide 1.

``EditorialAutoCoverStore`` gives the selector fresh reads (one session per
call, so a poll never sees a cached row) and the write: the generated asset
as an ``ai_image`` ``slide_cover`` through the existing cover switch with
rendering off (stage, project lock, lock-version CAS, store). The owner-choice
check is repeated on the write's own read, right before the CAS.

``autopilot_cover_task`` wraps the autopilot's generation run: only a
``succeeded`` run is followed by the selection; a failed one leaves slide 1
alone. Manual generations never go through it.

The ORM, repositories and the carousel services are imported lazily (the
editorial facade loads while the ORM registry is still initialising).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverSelector,
    AutoCoverWrite,
    ProjectAtVersion,
    choice_refusal,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_CRASHED,
    REASON_AUTO_SELECT_ASSET_GONE,
    REASON_AUTO_SELECT_NO_PROJECT,
)
from rag_backend.domain.constants.slide_cover import COVER_KIND_AI_IMAGE
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.domain.models.slide_cover import SlideCover

logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], AsyncSession]


class EditorialAutoCoverStore:
    """``AutoCoverStore`` with a fresh session per call."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def result_asset(self, generation_id: UUID) -> UUID | None:
        """The stored result of a succeeded generation, else None."""
        from rag_backend.modules.editorial.infrastructure.cover_generations import (
            SqlCoverGenerationRepository,
        )

        async with self._sessions() as session:
            generation = await SqlCoverGenerationRepository(session).get(generation_id)
        if generation is None:
            return None
        if generation.status is not CoverGenerationStatus.SUCCEEDED:
            return None
        return generation.result_asset_id

    async def load(self, project_id: str) -> ProjectAtVersion | None:
        """The committed project and its lock version."""
        from rag_backend.modules.editorial.infrastructure import (
            CarouselProjectWriteOwner,
            LegacyCarouselAcl,
        )

        async with self._sessions() as session:
            acl = LegacyCarouselAcl(session, CarouselProjectWriteOwner(session))
            view = await acl.load_editorial(project_id)
        if view is None:
            return None
        return ProjectAtVersion(
            project=view.project.project, lock_version=view.lock_version
        )

    async def write(self, command: AutoCoverWrite) -> str:
        """Stage and store the cover under the CAS; no re-render."""
        async with self._sessions() as session:
            return await _write(session, command)


async def _write(session: AsyncSession, command: AutoCoverWrite) -> str:
    from rag_backend.application.services.carousel.slide_cover_switch import (
        SlideCoverSwitchCommand,
    )
    from rag_backend.modules.editorial.infrastructure.carousel_automation import (
        CarouselAutomationAcl,
    )
    from rag_backend.modules.editorial.infrastructure.carousel_cover import (
        slide_cover_switch_service,
    )

    project = await CarouselAutomationAcl(session).load_project(command.project_id)
    if project is None:
        return REASON_AUTO_SELECT_NO_PROJECT
    refusal = choice_refusal(project, command.baseline, command.asset_id)
    if refusal is not None:
        return refusal
    asset = await _generated_asset(session, command)
    if asset is None:
        return REASON_AUTO_SELECT_ASSET_GONE
    cover = SlideCover(
        asset_id=asset.id, kind=COVER_KIND_AI_IMAGE, staged_path=asset.relative_path
    )
    result = await slide_cover_switch_service(session, render=False).switch(
        SlideCoverSwitchCommand(
            project_id=command.project_id,
            expected_version=command.expected_version,
            cover=cover,
        )
    )
    return result.status


async def _generated_asset(
    session: AsyncSession, command: AutoCoverWrite
) -> CarouselCreatorAsset | None:
    """The carousel's generated cover ``asset_id`` whose file still exists."""
    from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
        EditorialGeneratedCovers,
    )

    covers = await EditorialGeneratedCovers(session).covers(command.project_id)
    return next((asset for asset in covers if asset.id == command.asset_id), None)


def auto_cover_selector() -> AutoCoverSelector:
    """The selector over the process session maker."""
    from rag_backend.infrastructure.database.config import get_session_maker

    return AutoCoverSelector(EditorialAutoCoverStore(get_session_maker()))


async def _select(selection: AutoCoverSelection) -> None:
    """Run the selection; a crash is logged and never escapes the task."""
    try:
        await auto_cover_selector().select(selection)
    except Exception:
        logger.exception(
            LOG_COVER_AUTO_SELECT,
            outcome=OUTCOME_AUTO_SELECT_CRASHED,
            project_id=selection.project_id,
            generation_id=str(selection.generation_id),
        )


def autopilot_cover_task(
    generate: Callable[[], Awaitable[object]], selection: AutoCoverSelection
) -> Callable[[], Awaitable[object]]:
    """``generate``, then the selection only when it ``succeeded``."""

    async def _execute() -> object:
        status = await generate()
        if status is CoverGenerationStatus.SUCCEEDED:
            await _select(selection)
        return status

    return _execute


__all__ = [
    "EditorialAutoCoverStore",
    "auto_cover_selector",
    "autopilot_cover_task",
]
