"""Accept one GrokBot cover upload (AE-0418, ADR-0024).

The form is checked first (``kind``, a screenshot's ``source_url``), then the
image store validates and stores the bytes as a creator asset with role
``cover``; the cover row (``asset_id`` = its id) is committed last. Every
refusal raises ``CoverAssetError`` with the public contract code.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import structlog

from rag_backend.domain.constants.slide_cover import COVER_KIND_SCREENSHOT
from rag_backend.domain.models.slide_cover import CoverAssetError
from rag_backend.modules.autopilot.cover_constants import (
    LOG_COVER,
    LOG_COVER_REJECTED,
    LOG_COVER_UPLOADED,
)
from rag_backend.modules.autopilot.domain.cover import (
    CoverAsset,
    CoverForm,
    clean_source,
    form_problem,
)
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverAssetStore,
    CoverImage,
    CoverImageStore,
)
from rag_backend.modules.autopilot.domain.ports import Clock

logger = structlog.get_logger()


class CoverOwnerMissingError(RuntimeError):
    """No autopilot owner user is configured: the cover has no owner."""


@dataclass(frozen=True, kw_only=True)
class CoverUploadDependencies:
    """The cover rows, the image store, the clock and the owner user id."""

    covers: CoverAssetStore
    images: CoverImageStore
    clock: Clock
    owner_user_id: str


@dataclass(frozen=True, kw_only=True)
class CoverUploadCommand:
    """The uploaded bytes and the form fields as received."""

    content: bytes
    kind: str | None
    source_url: str | None


@dataclass(frozen=True, kw_only=True)
class CoverUploadResult:
    """The 201 body: the asset id, its kind and final size."""

    asset_id: UUID
    kind: str
    width: int
    height: int


class CoverUploadService:
    """Validate, store and record one cover."""

    def __init__(self, deps: CoverUploadDependencies) -> None:
        self._deps = deps

    async def upload(self, command: CoverUploadCommand) -> CoverUploadResult:
        """The stored cover; raises ``CoverAssetError`` or a missing owner."""
        form = CoverForm(kind=command.kind, source_url=command.source_url)
        problem = form_problem(form)
        if problem is not None:
            _log_rejected(problem)
            raise CoverAssetError(problem)
        owner = self._deps.owner_user_id.strip()
        if not owner:
            raise CoverOwnerMissingError
        kind = str(command.kind)
        try:
            stored = await self._deps.images.store_image(
                CoverImage(owner_id=owner, content=command.content, kind=kind)
            )
        except CoverAssetError as exc:
            _log_rejected(exc.code)
            raise
        cover = CoverAsset(
            asset_id=uuid4(),
            creator_asset_id=stored.creator_asset_id,
            kind=kind,
            source_url=_source(form),
            width=stored.width,
            height=stored.height,
            created_at=self._deps.clock.now(),
        )
        await self._deps.covers.add_cover(cover)
        await self._deps.covers.commit()
        logger.info(LOG_COVER, outcome=LOG_COVER_UPLOADED, asset_id=str(cover.asset_id))
        return CoverUploadResult(
            asset_id=cover.asset_id, kind=kind, width=cover.width, height=cover.height
        )


def _source(form: CoverForm) -> str | None:
    """Only a screenshot keeps its source (an ai_image's is ignored)."""
    if form.kind != COVER_KIND_SCREENSHOT:
        return None
    return clean_source(form.source_url)


def _log_rejected(code: str) -> None:
    logger.info(LOG_COVER, outcome=LOG_COVER_REJECTED, code=code)


__all__ = [
    "CoverOwnerMissingError",
    "CoverUploadCommand",
    "CoverUploadDependencies",
    "CoverUploadResult",
    "CoverUploadService",
]
