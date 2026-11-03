"""``PUT /carousels/{id}/hook-photo`` follows the cover picker's rule for slide 1.

Binding another slide-1 photo changes slide 1 like the cover picker does, so a
completed carousel goes through the very same switch (``switch_hook_photo``:
``SlideCoverSwitchService`` with a ``HookPhotoChoice``): the project lock and
the lock-version CAS at the version read now, one commit for the photo, the
needs-republish marker and, on an approved carousel (Pedro's decision,
2026-11-02), the dropped approval; then the render, before the caller asks for
a new Telegram review. A released carousel is refused with
``cover_switch_requires_review`` (409), checked again under the lock. A
carousel that is not completed has no render or approval to protect; it is only
refused when released (``refuse_published``).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import (
    reopen_refusal,
)
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetService,
    HookPhotoCommand,
)
from rag_backend.application.services.carousel.slide_cover_switch import (
    HookPhotoChoice,
    SlideCoverSwitchCommand,
    SlideCoverSwitchResult,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.modules.editorial.public import (
    CheckpointReopener,
    EditorialReviewState,
    current_lock_version,
    slide_cover_switch_service,
)


async def refuse_published(session: AsyncSession, project_id: str) -> None:
    """409 ``cover_switch_requires_review`` for a released carousel."""
    state = await EditorialReviewState(session).review_state(project_id)
    if state is not None and reopen_refusal(state) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_COVER_SWITCH_REQUIRES_REVIEW,
        )


@dataclass(frozen=True, kw_only=True)
class HookPhotoChange:
    """A validated photo for slide 1 of a completed carousel, and how to bind it."""

    session: AsyncSession
    service: CreatorAssetService
    command: HookPhotoCommand
    asset: CarouselCreatorAsset


async def switch_hook_photo(
    change: HookPhotoChange, checkpoint: CheckpointReopener
) -> SlideCoverSwitchResult:
    """Stage, then store and re-render through the cover switch."""
    project_id = str(change.command.project.id)
    version = await current_lock_version(change.session, project_id)
    if version is None:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_VERSION_CONFLICT)
        )
    change.service.stage_hook_photo(change.command, change.asset)
    switch = slide_cover_switch_service(change.session, checkpoint)
    return await switch.switch(
        SlideCoverSwitchCommand(
            project_id=project_id,
            expected_version=version,
            cover=None,
            hook_photo=HookPhotoChoice(
                asset_id=change.asset.id, staged_path=change.asset.relative_path
            ),
        )
    )


__all__ = ["HookPhotoChange", "refuse_published", "switch_hook_photo"]
