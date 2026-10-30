"""Query parsing for ``GET /api/autopilot/ig-insights``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.modules.autopilot.domain.ig_media import (
    IgInsightsRequest,
    ResolvedIgQuery,
)
from rag_backend.modules.autopilot.ig_media_constants import (
    ERR_LIMIT_INVALID,
    ERR_MEDIA_TYPE_INVALID,
    ERR_PRODUCT_TYPE_INVALID,
    ERR_REFRESH_INVALID,
    ERR_SINCE_TOO_OLD,
    ERR_TIMESTAMP_INVALID,
    ERR_WINDOW_INVALID,
    IG_INSIGHTS_DEFAULT_LIMIT,
    IG_INSIGHTS_DEFAULT_SINCE_DAYS,
    IG_INSIGHTS_MAX_LIMIT,
    IG_INSIGHTS_MAX_SINCE_DAYS,
    MEDIA_TYPES,
    PRODUCT_TYPES,
    REFRESH_FALSE,
    REFRESH_TRUE,
)


class IgInsightsQueryError(Exception):
    """The insights query is outside the contract. ``code`` is the HTTP detail."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def resolve_query(request: IgInsightsRequest, now: datetime) -> ResolvedIgQuery:
    """Apply defaults and reject a window older than 90 days or inverted."""
    since = request.since or (now - timedelta(days=IG_INSIGHTS_DEFAULT_SINCE_DAYS))
    until = request.until or now
    if since < now - timedelta(days=IG_INSIGHTS_MAX_SINCE_DAYS):
        raise IgInsightsQueryError(ERR_SINCE_TOO_OLD)
    if since >= until:
        raise IgInsightsQueryError(ERR_WINDOW_INVALID)
    return ResolvedIgQuery(
        since=since,
        until=until,
        limit=request.limit,
        media_type=request.media_type,
        product_type=request.product_type,
        refresh=request.refresh,
    )


def parse_limit(value: str | None) -> int:
    """Default 30. Non-integers and values outside 1-100 are rejected."""
    if value is None or value == "":
        return IG_INSIGHTS_DEFAULT_LIMIT
    if not value.isdigit():
        raise IgInsightsQueryError(ERR_LIMIT_INVALID)
    number = int(value)
    if number < 1 or number > IG_INSIGHTS_MAX_LIMIT:
        raise IgInsightsQueryError(ERR_LIMIT_INVALID)
    return number


def parse_timestamp(value: str | None) -> datetime | None:
    """ISO-8601, or None when the parameter is absent."""
    if value is None or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IgInsightsQueryError(ERR_TIMESTAMP_INVALID) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def parse_choice(value: str | None, allowed: frozenset[str], code: str) -> str | None:
    """None when absent. A value outside ``allowed`` raises ``code``."""
    if value is None or value == "":
        return None
    if value not in allowed:
        raise IgInsightsQueryError(code)
    return value


def parse_refresh(value: str | None) -> bool:
    """Absent is false. Anything other than the true/false tokens is rejected."""
    if value is None or value == "":
        return False
    if value in REFRESH_TRUE:
        return True
    if value in REFRESH_FALSE:
        return False
    raise IgInsightsQueryError(ERR_REFRESH_INVALID)


def media_type_or_raise(value: str | None) -> str | None:
    """Allowlisted media type, or None."""
    return parse_choice(value, MEDIA_TYPES, ERR_MEDIA_TYPE_INVALID)


def product_type_or_raise(value: str | None) -> str | None:
    """Allowlisted product type, or None."""
    return parse_choice(value, PRODUCT_TYPES, ERR_PRODUCT_TYPE_INVALID)


__all__ = [
    "IgInsightsQueryError",
    "media_type_or_raise",
    "parse_limit",
    "parse_refresh",
    "parse_timestamp",
    "product_type_or_raise",
    "resolve_query",
]
