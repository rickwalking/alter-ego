"""Autopilot HTTP routes.

Every route on this router requires the service API key. Decorate each
route with the shared slowapi limit (``RATE_LIMIT_AUTOPILOT`` /
``RATE_LIMIT_SCOPE_AUTOPILOT``) so they share one 10/minute budget per IP.
the cover upload (``assets.py``) has its own 30/minute limit.

A topic-intake rejection carries ``field`` only when one field caused it
(``response_model_exclude_none``). ``POST /assets`` (the GrokBot cover upload)
is included under the same guard.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.modules.autopilot.api.assets import router as cover_assets_router
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.dependencies import (
    build_scout_failure,
    build_topic_intake,
    build_x_signals,
    clock_from,
)
from rag_backend.modules.autopilot.api.mapping import command_from, response_from
from rag_backend.modules.autopilot.api.schemas import (
    ScoutFailedBody,
    ScoutFailedResponse,
    TopicBatch,
    TopicIntakeResponse,
    XSignalsBatch,
    XSignalsResponse,
)
from rag_backend.modules.autopilot.api.scout_mapping import (
    scout_command,
    x_signals_command,
    x_signals_response,
)
from rag_backend.modules.autopilot.application.scout_failure import ScoutFailureService
from rag_backend.modules.autopilot.application.topic_intake import TopicIntakeService
from rag_backend.modules.autopilot.application.x_signals import XSignalsService
from rag_backend.modules.autopilot.bootstrap import (
    default_signals_service,
    remember_served_signal_urls,
)
from rag_backend.modules.autopilot.constants import (
    APP_STATE_SIGNALS,
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    DETAIL_SCOUT_NOTIFY_FAILED,
    DETAIL_SCOUT_REASON_EMPTY,
    PATH_SCOUT_FAILED,
    PATH_SIGNALS,
    PATH_TOPICS,
    PATH_X_SIGNALS,
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.ports import SignalsReader
from rag_backend.modules.autopilot.domain.signals import SignalsBundle
from rag_backend.modules.autopilot.scout_constants import SCOUT_SUPPRESSED_DETAILS

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@router.get(
    PATH_SIGNALS,
    response_model=SignalsBundle,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_autopilot_signals(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SignalsBundle:
    """Return the deduped signal bundle and remember its URLs for 6 hours."""
    reader = signals_reader(request)
    bundle = await reader.collect_all()
    await remember_served_signal_urls(session, bundle, clock_from(request).now())
    return bundle


@router.post(
    PATH_TOPICS,
    response_model=TopicIntakeResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def post_autopilot_topics(
    request: Request,
    batch: TopicBatch,
    service: Annotated[TopicIntakeService, Depends(build_topic_intake)],
) -> TopicIntakeResponse:
    """Store accepted topics and queue runs that still fit today's cap."""
    del request
    result = await service.accept(command_from(batch))
    return response_from(result)


@router.post(
    PATH_X_SIGNALS,
    response_model=XSignalsResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def post_autopilot_x_signals(
    request: Request,
    batch: XSignalsBatch,
    service: Annotated[XSignalsService, Depends(build_x_signals)],
) -> XSignalsResponse:
    """Store recent X status posts and allowlist their canonical URLs."""
    del request
    result = await service.accept(x_signals_command(batch))
    return x_signals_response(result)


@router.post(
    PATH_SCOUT_FAILED,
    response_model=ScoutFailedResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def post_autopilot_scout_failed(
    request: Request,
    body: ScoutFailedBody,
    service: Annotated[ScoutFailureService, Depends(build_scout_failure)],
) -> ScoutFailedResponse:
    """Send the owner one Telegram message containing the scout's reason."""
    del request
    result = await service.report(scout_command(body.reason))
    if result.delivered:
        return ScoutFailedResponse(delivered=True)
    if result.error in SCOUT_SUPPRESSED_DETAILS:
        return ScoutFailedResponse(delivered=False)
    detail = result.error or DETAIL_SCOUT_NOTIFY_FAILED
    raise HTTPException(status_code=_failure_status(detail), detail=detail)


router.include_router(cover_assets_router)


def _failure_status(error: str) -> int:
    """Empty reasons are a client error. Delivery problems are unavailable."""
    if error == DETAIL_SCOUT_REASON_EMPTY:
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_503_SERVICE_UNAVAILABLE


def signals_reader(request: Request) -> SignalsReader:
    """Prefer an app-state override, otherwise the process service."""
    override: object = getattr(request.app.state, APP_STATE_SIGNALS, None)
    if override is None:
        return default_signals_service()
    return cast(SignalsReader, override)
