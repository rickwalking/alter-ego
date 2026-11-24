"""``POST /api/autopilot/assets/video``: the scout uploads a Reel's source video.

One multipart ``file`` part, at most 200 MB, streamed to disk. The answer is
the ``asset_id`` a repost draft names as ``source_asset_id``. Refusals are 4xx
with ``{"detail": "<code>"}``, like the cover upload.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT_ASSETS
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.repost_schemas import SourceVideoResponse
from rag_backend.modules.autopilot.application.repost_source_upload import (
    RepostSourceUploads,
    SourceUpload,
)
from rag_backend.modules.autopilot.bootstrap_repost import (
    repost_files_root,
    repost_source_uploads,
)
from rag_backend.modules.autopilot.constants import ROUTER_PREFIX, TAG_AUTOPILOT
from rag_backend.modules.autopilot.domain.repost_source import SourceError
from rag_backend.modules.autopilot.infrastructure.repost_source_files import (
    part_path,
    write_chunks,
)
from rag_backend.modules.autopilot.repost_source_constants import (
    ERR_SOURCE_MISSING,
    FORM_FIELD_SOURCE_FILE,
    HTTP_CREATED,
    HTTP_UNPROCESSABLE,
    PATH_SOURCE_VIDEO,
    SOURCE_CHUNK_BYTES,
    SOURCE_KIND_VIDEO,
    STATUS_BY_SOURCE_ERROR,
)

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@dataclass(frozen=True, kw_only=True)
class SourceBundle:
    """The use case and the folder the route streams into."""

    uploads: RepostSourceUploads
    root: Path


def source_bundle(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SourceBundle:
    """Wire the upload for this request."""
    return SourceBundle(
        uploads=repost_source_uploads(session, settings),
        root=repost_files_root(settings),
    )


@router.post(
    PATH_SOURCE_VIDEO, status_code=HTTP_CREATED, response_model=SourceVideoResponse
)
@limiter.limit(RATE_LIMIT_AUTOPILOT_ASSETS)
async def post_source_video(
    request: Request,
    bundle: Annotated[SourceBundle, Depends(source_bundle)],
    file: Annotated[UploadFile | None, File(alias=FORM_FIELD_SOURCE_FILE)] = None,
) -> SourceVideoResponse:
    """Store one source video and return its ``asset_id``."""
    del request
    if file is None:
        raise HTTPException(
            status_code=_status(ERR_SOURCE_MISSING), detail=ERR_SOURCE_MISSING
        )
    asset_id = uuid4()
    part = part_path(bundle.root, asset_id)
    try:
        size = await write_chunks(_chunks(file), part)
        source = await bundle.uploads.accept(
            SourceUpload(asset_id=asset_id, part=part, size_bytes=size)
        )
    except SourceError as exc:
        raise HTTPException(status_code=_status(exc.code), detail=exc.code) from None
    return SourceVideoResponse(
        asset_id=str(source.id),
        kind=SOURCE_KIND_VIDEO,
        width=source.probe.width,
        height=source.probe.height,
        duration_s=source.probe.duration_s,
        size_bytes=source.size_bytes,
    )


async def _chunks(file: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await file.read(SOURCE_CHUNK_BYTES):
        yield chunk


def _status(code: str) -> int:
    return STATUS_BY_SOURCE_ERROR.get(code, HTTP_UNPROCESSABLE)


__all__ = ["router", "source_bundle"]
