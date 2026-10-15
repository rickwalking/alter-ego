"""``GET /api/instagram/insights``: the dashboard's Instagram KPIs (AE-0378).

Editor or admin only. Each published post is served from its stored snapshot
and read again from Graph when the snapshot is older than six hours (see
``InstagramInsightsService``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, cast

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies import require_editor_or_admin
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.api.dependencies import clock_from
from rag_backend.modules.autopilot.api.insights_mapping import insights_response
from rag_backend.modules.autopilot.api.schemas import InstagramInsightsResponse
from rag_backend.modules.autopilot.application.insights_service import (
    InsightsDependencies,
    InstagramInsightsService,
)
from rag_backend.modules.autopilot.domain.insights import InsightsGateway
from rag_backend.modules.autopilot.infrastructure.insights_gateway import (
    build_insights_gateway,
)
from rag_backend.modules.autopilot.infrastructure.insights_store import (
    SqlInsightsStore,
)
from rag_backend.modules.autopilot.insights_constants import (
    APP_STATE_INSIGHTS_GATEWAY,
    INSIGHTS_HTTP_TIMEOUT_SECONDS,
    INSIGHTS_ROUTER_PREFIX,
    PATH_INSIGHTS,
    TAG_INSTAGRAM,
)

router = APIRouter(
    prefix=INSIGHTS_ROUTER_PREFIX,
    tags=[TAG_INSTAGRAM],
    dependencies=[Depends(require_editor_or_admin)],
)


@dataclass(frozen=True)
class _Insights:
    service: InstagramInsightsService
    configured: bool


async def _insights(
    request: Request, session: Annotated[AsyncSession, Depends(get_db)]
) -> AsyncIterator[_Insights]:
    async with httpx.AsyncClient(timeout=INSIGHTS_HTTP_TIMEOUT_SECONDS) as client:
        gateway = _installed_gateway(request) or build_insights_gateway(
            get_settings(), client
        )
        yield _Insights(
            service=InstagramInsightsService(
                InsightsDependencies(
                    store=SqlInsightsStore(session),
                    clock=clock_from(request),
                    gateway=gateway,
                )
            ),
            configured=gateway is not None,
        )


def _installed_gateway(request: Request) -> InsightsGateway | None:
    """A test double on ``app.state``, else None."""
    override: object = getattr(request.app.state, APP_STATE_INSIGHTS_GATEWAY, None)
    if override is None:
        return None
    return cast(InsightsGateway, override)


@router.get(PATH_INSIGHTS, response_model=InstagramInsightsResponse)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_instagram_insights(
    request: Request, insights: Annotated[_Insights, Depends(_insights)]
) -> InstagramInsightsResponse:
    """Per-post views, reach, saves, shares, follows and profile visits."""
    del request
    report = await insights.service.report()
    return insights_response(report, configured=insights.configured)


__all__ = ["router"]
