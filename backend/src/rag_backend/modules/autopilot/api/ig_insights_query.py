"""Parse ``GET /api/autopilot/ig-insights`` query parameters."""

from __future__ import annotations

from fastapi import Request

from rag_backend.modules.autopilot.domain.ig_insights_query import (
    media_type_or_raise,
    parse_limit,
    parse_refresh,
    parse_timestamp,
    product_type_or_raise,
)
from rag_backend.modules.autopilot.domain.ig_media import IgInsightsRequest
from rag_backend.modules.autopilot.ig_media_constants import (
    QUERY_LIMIT,
    QUERY_MEDIA_TYPE,
    QUERY_PRODUCT_TYPE,
    QUERY_REFRESH,
    QUERY_SINCE,
    QUERY_UNTIL,
)


def query_from(request: Request) -> IgInsightsRequest:
    """Read the six query keys. Invalid values raise ``IgInsightsQueryError``."""
    params = request.query_params
    return IgInsightsRequest(
        since=parse_timestamp(params.get(QUERY_SINCE)),
        until=parse_timestamp(params.get(QUERY_UNTIL)),
        limit=parse_limit(params.get(QUERY_LIMIT)),
        media_type=media_type_or_raise(params.get(QUERY_MEDIA_TYPE)),
        product_type=product_type_or_raise(params.get(QUERY_PRODUCT_TYPE)),
        refresh=parse_refresh(params.get(QUERY_REFRESH)),
    )


__all__ = ["query_from"]
