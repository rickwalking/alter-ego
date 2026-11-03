"""``CoverImageStore`` and ``CoverSwitcher`` over the editorial facade.

The image rules, the WebP storage and the republish re-render belong to the
carousel side; the autopilot reaches them only through
``rag_backend.modules.editorial.public``.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
    REASON_REVIEW_NOT_REOPENED,
)
from rag_backend.modules.autopilot.cover_constants import (
    LOG_COVER,
    LOG_COVER_RENDER_FAILED,
)
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverImage,
    CoverSwitchCommand,
    CoverSwitchStatus,
    StoredImage,
)
from rag_backend.modules.editorial.public import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
    CheckpointReopener,
    CoverImageRequest,
    CoverSwitchRequest,
    cover_image_file,
    delete_cover_images,
    store_cover_image,
    switch_slide_cover,
)

logger = structlog.get_logger()

_SWITCH_STATUS: dict[str, CoverSwitchStatus] = {
    AUTOFIX_STATUS_FIXED: CoverSwitchStatus.SWITCHED,
    AUTOFIX_STATUS_CONFLICT: CoverSwitchStatus.CONFLICT,
    ERR_COVER_SWITCH_REQUIRES_REVIEW: CoverSwitchStatus.REQUIRES_REVIEW,
    REASON_REVIEW_NOT_REOPENED: CoverSwitchStatus.REQUIRES_REVIEW,
}


class EditorialCoverImages:
    """Validate, store, read and delete cover images (creator assets)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_image(self, image: CoverImage) -> StoredImage:
        """Store a valid image; raises ``CoverAssetError`` with the code."""
        stored = await store_cover_image(
            CoverImageRequest(
                session=self._session,
                owner_id=image.owner_id,
                content=image.content,
                kind=image.kind,
            )
        )
        return StoredImage(
            creator_asset_id=stored.creator_asset_id,
            width=stored.width,
            height=stored.height,
        )

    async def image_file(self, creator_asset_id: UUID) -> str | None:
        """The stored WebP path, or None when it is gone."""
        path = await cover_image_file(self._session, creator_asset_id)
        return str(path) if path is not None else None

    async def delete_images(self, creator_asset_ids: tuple[UUID, ...]) -> int:
        """Delete cover images and their files."""
        return await delete_cover_images(self._session, creator_asset_ids)


class EditorialCoverSwitcher:
    """Re-render a finished carousel with or without the GrokBot cover.

    With ``checkpoint`` a switch on an approved carousel (a cancelled
    schedule) drops its approval; without it that carousel is refused.
    """

    def __init__(
        self, session: AsyncSession, checkpoint: CheckpointReopener | None = None
    ) -> None:
        self._session = session
        self._checkpoint = checkpoint

    async def switch(self, command: CoverSwitchCommand) -> CoverSwitchStatus:
        """Stage, store and re-render; a conflict writes nothing.

        A stored choice whose re-render reported errors is ``RENDER_FAILED``.
        """
        result = await switch_slide_cover(
            CoverSwitchRequest(
                session=self._session,
                project_id=command.project_id,
                expected_version=command.expected_version,
                cover=command.cover,
                checkpoint=self._checkpoint,
            )
        )
        status = _SWITCH_STATUS.get(result.status, CoverSwitchStatus.MISSING)
        if status is CoverSwitchStatus.SWITCHED and result.render_errors:
            logger.warning(
                LOG_COVER,
                outcome=LOG_COVER_RENDER_FAILED,
                project_id=command.project_id,
                errors=list(result.render_errors),
            )
            return CoverSwitchStatus.RENDER_FAILED
        return status


__all__ = ["EditorialCoverImages", "EditorialCoverSwitcher"]
