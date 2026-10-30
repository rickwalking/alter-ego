"""``GET /api/autopilot/ig-insights`` for the boost bot.

The autopilot API key is required. The dashboard route is unchanged.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.dependencies import clock_from
from rag_backend.modules.autopilot.api.ig_insights_mapping import ig_insights_response
from rag_backend.modules.autopilot.api.ig_insights_query import query_from
from rag_backend.modules.autopilot.api.ig_insights_schemas import IgInsightsResponse
from rag_backend.modules.autopilot.application.ig_insights_service import (
    IgInsightsDependencies,
    IgInsightsService,
)
from rag_backend.modules.autopilot.constants import (
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.ig_insights_query import (
    IgInsightsQueryError,
    resolve_query,
)
from rag_backend.modules.autopilot.domain.ig_media import MediaListGateway
from rag_backend.modules.autopilot.domain.insights import InsightsGateway
from rag_backend.modules.autopilot.ig_media_constants import (
    APP_STATE_IG_MEDIA_GATEWAY,
    CACHE_CONTROL_NO_STORE,
    HEADER_CACHE_CONTROL,
    PATH_IG_INSIGHTS,
)
from rag_backend.modules.autopilot.infrastructure.boost_store import SqlBoostStore
from rag_backend.modules.autopilot.infrastructure.ig_media_gateway import (
    build_ig_media_gateway,
)
from rag_backend.modules.autopilot.infrastructure.ig_media_store import SqlIgMediaStore
from rag_backend.modules.autopilot.infrastructure.insights_gateway import (
    build_insights_gateway,
)
from rag_backend.modules.autopilot.infrastructure.insights_store import SqlInsightsStore
from rag_backend.modules.autopilot.insights_constants import (
    APP_STATE_INSIGHTS_GATEWAY,
    INSIGHTS_HTTP_TIMEOUT_SECONDS,
)

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@dataclass(frozen=True)
class _Bundle:
    service: IgInsightsService


async def _bundle(
    request: Request, session: Annotated[AsyncSession, Depends(get_db)]
) -> AsyncIterator[_Bundle]:
    async with httpx.AsyncClient(timeout=INSIGHTS_HTTP_TIMEOUT_SECONDS) as client:
        media_gateway = _media_gateway(request, client)
        yield _Bundle(
            service=IgInsightsService(
                IgInsightsDependencies(
                    media=SqlIgMediaStore(session),
                    insights=SqlInsightsStore(session),
                    clock=clock_from(request),
                    media_gateway=media_gateway,
                    insights_gateway=_insights_gateway(request, client),
                    boosts=SqlBoostStore(session),
                )
            )
        )


def _media_gateway(
    request: Request, client: httpx.AsyncClient
) -> MediaListGateway | None:
    override: object = getattr(request.app.state, APP_STATE_IG_MEDIA_GATEWAY, None)
    if override is not None:
        return cast(MediaListGateway, override)
    return build_ig_media_gateway(get_settings(), client)


def _insights_gateway(
    request: Request, client: httpx.AsyncClient
) -> InsightsGateway | None:
    override: object = getattr(request.app.state, APP_STATE_INSIGHTS_GATEWAY, None)
    if override is not None:
        return cast(InsightsGateway, override)
    return build_insights_gateway(get_settings(), client)


@router.get(
    PATH_IG_INSIGHTS,
    response_model=IgInsightsResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_ig_insights(
    request: Request,
    response: Response,
    bundle: Annotated[_Bundle, Depends(_bundle)],
) -> IgInsightsResponse:
    """Account media with type-specific metrics, rates and baselines."""
    response.headers[HEADER_CACHE_CONTROL] = CACHE_CONTROL_NO_STORE
    try:
        query = resolve_query(query_from(request), clock_from(request).now())
    except IgInsightsQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.code
        ) from None
    report = await bundle.service.report(query)
    return ig_insights_response(report)


__all__ = ["router"]
