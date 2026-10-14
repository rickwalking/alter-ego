"""Autopilot HTTP routes.

Every route on this router requires the service API key. Decorate each
route with the shared slowapi limit (``RATE_LIMIT_AUTOPILOT`` /
``RATE_LIMIT_SCOPE_AUTOPILOT``) so they share one 10/minute budget per IP.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.dependencies import (
    build_topic_intake,
    clock_from,
)
from rag_backend.modules.autopilot.api.mapping import command_from, response_from
from rag_backend.modules.autopilot.api.schemas import TopicBatch, TopicIntakeResponse
from rag_backend.modules.autopilot.application.topic_intake import TopicIntakeService
from rag_backend.modules.autopilot.bootstrap import (
    default_signals_service,
    remember_served_signal_urls,
)
from rag_backend.modules.autopilot.constants import (
    APP_STATE_SIGNALS,
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    PATH_SIGNALS,
    PATH_TOPICS,
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.ports import SignalsReader
from rag_backend.modules.autopilot.domain.signals import SignalsBundle

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


def signals_reader(request: Request) -> SignalsReader:
    """Prefer an app-state override, otherwise the process service."""
    override: object = getattr(request.app.state, APP_STATE_SIGNALS, None)
    if override is None:
        return default_signals_service()
    return cast(SignalsReader, override)
