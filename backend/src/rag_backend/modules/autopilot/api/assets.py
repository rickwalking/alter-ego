"""``POST /api/autopilot/assets``: GrokBot uploads a slide-1 cover (AE-0418).

Same API key as every autopilot route, with its own rate limit (30/minute,
not the shared 10/minute budget of the other routes). One multipart
``file`` part (PNG or JPEG, at most 5 MB) plus ``kind`` and, for a
screenshot, ``source_url``. Refusals are 4xx with ``{"detail": "<code>"}``
(contract: ``docs/architecture/grokbot-cover-asset.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_MAX_BYTES
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT_ASSETS
from rag_backend.domain.models.slide_cover import CoverAssetError
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.api.dependencies import clock_from
from rag_backend.modules.autopilot.api.schemas import CoverAssetResponse
from rag_backend.modules.autopilot.application.cover_upload import (
    CoverOwnerMissingError,
    CoverUploadCommand,
    CoverUploadDependencies,
    CoverUploadService,
)
from rag_backend.modules.autopilot.cover_constants import (
    DETAIL_COVER_OWNER_UNCONFIGURED,
    FORM_FIELD_FILE,
    FORM_FIELD_KIND,
    FORM_FIELD_SOURCE_URL,
    HTTP_UNAVAILABLE,
    HTTP_UNPROCESSABLE,
    PATH_ASSETS,
    UPLOAD_READ_SLACK_BYTES,
    UPLOAD_STATUS_BY_CODE,
)
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore

_HTTP_CREATED = 201

# Included by ``api/router.py``: it inherits the prefix, tag and API-key guard.
router = APIRouter()


def build_cover_upload(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CoverUploadService:
    """Wire the upload for this request."""
    return CoverUploadService(
        CoverUploadDependencies(
            covers=SqlCoverAssetStore(session),
            images=EditorialCoverImages(session),
            clock=clock_from(request),
            owner_user_id=settings.autopilot_owner_user_id,
        )
    )


@dataclass(frozen=True, kw_only=True)
class _UploadForm:
    """The multipart parts as received (each may be missing)."""

    file: UploadFile | None
    kind: str | None
    source_url: str | None


def upload_form(
    file: Annotated[UploadFile | None, File(alias=FORM_FIELD_FILE)] = None,
    kind: Annotated[str | None, Form(alias=FORM_FIELD_KIND)] = None,
    source_url: Annotated[str | None, Form(alias=FORM_FIELD_SOURCE_URL)] = None,
) -> _UploadForm:
    """Collect the parts; the use case decides what a missing one means."""
    return _UploadForm(file=file, kind=kind, source_url=source_url)


@router.post(PATH_ASSETS, status_code=_HTTP_CREATED, response_model=CoverAssetResponse)
@limiter.limit(RATE_LIMIT_AUTOPILOT_ASSETS)
async def post_autopilot_asset(
    request: Request,
    service: Annotated[CoverUploadService, Depends(build_cover_upload)],
    form: Annotated[_UploadForm, Depends(upload_form)],
) -> CoverAssetResponse:
    """Store one cover and return its ``asset_id`` and final size."""
    del request
    command = CoverUploadCommand(
        content=await _read(form.file), kind=form.kind, source_url=form.source_url
    )
    try:
        result = await service.upload(command)
    except CoverAssetError as exc:
        status = UPLOAD_STATUS_BY_CODE.get(exc.code, HTTP_UNPROCESSABLE)
        raise HTTPException(status_code=status, detail=exc.code) from None
    except CoverOwnerMissingError:
        raise HTTPException(
            status_code=HTTP_UNAVAILABLE, detail=DETAIL_COVER_OWNER_UNCONFIGURED
        ) from None
    return CoverAssetResponse(
        asset_id=result.asset_id,
        kind=result.kind,
        width=result.width,
        height=result.height,
    )


async def _read(file: UploadFile | None) -> bytes:
    """At most one byte past the cap (an oversized body is detected, not kept).

    A missing file part reads as empty bytes: not a PNG or JPEG.
    """
    if file is None:
        return b""
    return await file.read(CREATOR_ASSET_MAX_BYTES + UPLOAD_READ_SLACK_BYTES)


__all__ = ["build_cover_upload", "router", "upload_form"]
