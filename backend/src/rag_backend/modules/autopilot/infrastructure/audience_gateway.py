"""Graph ``online_followers`` reader.

``GET /{ig-user-id}/insights?metric=online_followers&period=lifetime`` returns
one entry per recent day, each ``{"value": {"0": n, ..., "23": n}}`` keyed by
UTC hour. The hours are summed over the days. Any failure (HTTP, a refused
metric, a missing token, a non-JSON body) raises ``InstagramCallError``; the
signal source logs it and falls back.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_graph_payloads import (
    error_from,
    json_dict,
)
from rag_backend.infrastructure.external.instagram_publisher_factory import (
    token_provider_for,
)
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisherConfig,
)
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import guard_graph
from rag_backend.modules.autopilot.insights_constants import (
    FIELD_DATA,
    FIELD_METRIC,
    FIELD_NAME,
    FIELD_VALUE,
    FIELD_VALUES,
)
from rag_backend.modules.autopilot.recommend_constants import (
    AUDIENCE_HTTP_TIMEOUT_SECONDS,
    FIELD_PERIOD,
    GRAPH_PATH_USER_INSIGHTS,
    HOURS_PER_DAY,
    METRIC_ONLINE_FOLLOWERS,
    PERIOD_LIFETIME,
)

ClientFactory = Callable[[], httpx.AsyncClient]


def _default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=AUDIENCE_HTTP_TIMEOUT_SECONDS)


class GraphAudienceGateway:
    """``AudienceGateway`` over the Instagram Graph API."""

    def __init__(
        self,
        config: MetaInstagramPublisherConfig,
        client_factory: ClientFactory = _default_client,
    ) -> None:
        self._config = config
        self._client_factory = client_factory

    async def online_followers(self) -> dict[int, int]:
        """Followers online per UTC hour, summed over the days Graph returns."""
        return await guard_graph(self._read)

    async def _read(self) -> dict[int, int]:
        token = await self._config.token_provider.get()
        if not token or not self._config.ig_user_id:
            raise RuntimeError(ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED)
        path = GRAPH_PATH_USER_INSIGHTS.format(ig_user_id=self._config.ig_user_id)
        params = {
            FIELD_METRIC: METRIC_ONLINE_FOLLOWERS,
            FIELD_PERIOD: PERIOD_LIFETIME,
            COOKIE_ACCESS_TOKEN: token,
        }
        async with (
            self._client_factory() as client,
            asyncio.timeout(AUDIENCE_HTTP_TIMEOUT_SECONDS),
        ):
            response = await client.get(
                self._config.graph_base.rstrip("/") + path, params=params
            )
        if not response.is_success:
            raise error_from(response)
        return parse_online_followers(json_dict(response))


def build_audience_gateway(settings: Settings) -> GraphAudienceGateway | None:
    """The reader for the configured account, or None without one."""
    if not settings.meta_ig_user_id.strip():
        return None
    return GraphAudienceGateway(
        MetaInstagramPublisherConfig(
            ig_user_id=settings.meta_ig_user_id,
            graph_base=settings.meta_ig_graph_base,
            token_provider=token_provider_for(settings),
        )
    )


def parse_online_followers(payload: dict[str, object]) -> dict[int, int]:
    """``{utc_hour: followers}`` summed over the days; odd entries are skipped."""
    data = payload.get(FIELD_DATA)
    totals: dict[int, int] = {}
    for item in data if isinstance(data, list) else []:
        if (
            not isinstance(item, dict)
            or item.get(FIELD_NAME) != METRIC_ONLINE_FOLLOWERS
        ):
            continue
        for hours in _day_values(item):
            _add_hours(totals, hours)
    return totals


def _day_values(item: dict[str, object]) -> list[dict[str, object]]:
    series = item.get(FIELD_VALUES)
    if not isinstance(series, list):
        return []
    values = [entry.get(FIELD_VALUE) for entry in series if isinstance(entry, dict)]
    return [value for value in values if isinstance(value, dict)]


def _add_hours(totals: dict[int, int], hours: dict[str, object]) -> None:
    for key, count in hours.items():
        if not key.isdigit() or isinstance(count, bool) or not isinstance(count, int):
            continue
        hour = int(key)
        if hour < HOURS_PER_DAY:
            totals[hour] = totals.get(hour, 0) + count


__all__ = [
    "GraphAudienceGateway",
    "build_audience_gateway",
    "parse_online_followers",
]
