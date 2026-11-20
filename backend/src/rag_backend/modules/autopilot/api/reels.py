"""``GET /api/autopilot/reels`` and ``/reels/{media_id}/video`` for the scout.

The video route streams the Reel's MP4 through the backend, so the scout
does not depend on an expiring CDN URL.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.repost_mapping import error_response, reels_view
from rag_backend.modules.autopilot.api.repost_schemas import ReelsView
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.reels_service import (
    ReelsDeps,
    ReelsService,
)
from rag_backend.modules.autopilot.constants import (
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.reels_query import parse_reels_query
from rag_backend.modules.autopilot.domain.repost import RepostError, RepostProblem
from rag_backend.modules.autopilot.domain.repost_ports import ReelGateway
from rag_backend.modules.autopilot.ig_media_constants import (
    CACHE_CONTROL_NO_STORE,
    HEADER_CACHE_CONTROL,
    PRODUCT_REELS,
)
from rag_backend.modules.autopilot.infrastructure.insights_gateway import (
    build_insights_gateway,
)
from rag_backend.modules.autopilot.infrastructure.insights_store import SqlInsightsStore
from rag_backend.modules.autopilot.infrastructure.reels_gateway import (
    build_reel_gateway,
)
from rag_backend.modules.autopilot.infrastructure.repost_store import SqlRepostStore
from rag_backend.modules.autopilot.infrastructure.repost_video import FfprobeReelProbe
from rag_backend.modules.autopilot.reels_constants import (
    REELS_HTTP_TIMEOUT_SECONDS,
    VIDEO_CHUNK_BYTES,
    VIDEO_STREAM_TIMEOUT_SECONDS,
)
from rag_backend.modules.autopilot.repost_constants import (
    ERR_NOT_CONFIGURED,
    ERR_REEL_NOT_FOUND,
    ERR_UNAVAILABLE,
    HTTP_NOT_FOUND,
    HTTP_UNAVAILABLE,
    MEDIA_TYPE_MP4,
    PATH_REEL_VIDEO,
    PATH_REELS,
)

_HEADER_CONTENT_LENGTH = "content-length"

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@dataclass(frozen=True, kw_only=True)
class ReelsBundle:
    """The list service and the Graph reader (None when unconfigured)."""

    service: ReelsService
    reels: ReelGateway | None


async def reels_bundle(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[ReelsBundle]:
    """Graph readers, caches and the probe for one request."""
    async with httpx.AsyncClient(timeout=REELS_HTTP_TIMEOUT_SECONDS) as client:
        reels = build_reel_gateway(settings, client)
        store = SqlRepostStore(session)
        service = ReelsService(
            ReelsDeps(
                reels=reels,
                insights_gateway=build_insights_gateway(settings, client),
                insights=SqlInsightsStore(session),
                facts=store,
                reposts=store,
                probe=FfprobeReelProbe(),
                clock=SystemClock(),
            )
        )
        yield ReelsBundle(service=service, reels=reels)


@router.get(PATH_REELS, response_model=ReelsView)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_reels(
    request: Request, bundle: Annotated[ReelsBundle, Depends(reels_bundle)]
) -> JSONResponse:
    """Reels aged ``min_age_days``..``max_age_days`` with metrics, sorted, paged."""
    try:
        query = parse_reels_query(dict(request.query_params))
        page = await bundle.service.page(query)
    except RepostError as exc:
        return error_response(exc)
    return JSONResponse(
        content=reels_view(page).model_dump(mode="json"),
        headers={HEADER_CACHE_CONTROL: CACHE_CONTROL_NO_STORE},
    )


@router.get(PATH_REEL_VIDEO)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_reel_video(
    request: Request,
    media_id: str,
    bundle: Annotated[ReelsBundle, Depends(reels_bundle)],
) -> Response:
    """The Reel's original MP4, streamed; 404 ``reel_not_found`` otherwise."""
    del request
    try:
        url = await _video_url(bundle.reels, media_id)
        return await stream_video(url)
    except RepostError as exc:
        return error_response(exc)


async def _video_url(reels: ReelGateway | None, media_id: str) -> str:
    if reels is None:
        raise _error(ERR_NOT_CONFIGURED, HTTP_UNAVAILABLE)
    try:
        reel = await reels.reel(media_id)
    except InstagramCallError:
        raise _error(ERR_UNAVAILABLE, HTTP_UNAVAILABLE) from None
    if reel is None or reel.product_type != PRODUCT_REELS or not reel.video_url:
        raise _error(ERR_REEL_NOT_FOUND, HTTP_NOT_FOUND)
    return reel.video_url


async def stream_video(url: str) -> StreamingResponse:
    """Open the CDN stream first, so a failure is a JSON error, not a cut body."""
    client = httpx.AsyncClient(timeout=VIDEO_STREAM_TIMEOUT_SECONDS)
    try:
        upstream = await client.send(client.build_request("GET", url), stream=True)
    except httpx.HTTPError:
        await client.aclose()
        raise _error(ERR_UNAVAILABLE, HTTP_UNAVAILABLE) from None
    if not upstream.is_success:
        await upstream.aclose()
        await client.aclose()
        raise _error(ERR_UNAVAILABLE, HTTP_UNAVAILABLE)
    headers = {HEADER_CACHE_CONTROL: CACHE_CONTROL_NO_STORE}
    length = upstream.headers.get(_HEADER_CONTENT_LENGTH)
    if length is not None:
        headers[_HEADER_CONTENT_LENGTH] = length
    return StreamingResponse(
        upstream.aiter_bytes(VIDEO_CHUNK_BYTES),
        media_type=MEDIA_TYPE_MP4,
        headers=headers,
        background=BackgroundTask(_close, upstream, client),
    )


async def _close(upstream: httpx.Response, client: httpx.AsyncClient) -> None:
    await upstream.aclose()
    await client.aclose()


def _error(code: str, status: int) -> RepostError:
    return RepostError(RepostProblem(code=code, status=status))


__all__ = ["ReelsBundle", "reels_bundle", "router", "stream_video"]
