"""Graph ``/{media-id}/insights`` reader (AE-0378, ADR-0021 D11).

Same host, user id and token provider as the publisher. All metrics are asked
in one call; when Graph refuses the list (a metric it does not offer for this
media, a permanent 4xx), each metric is asked alone and the refused ones stay
``None``. A transient failure, a missing token or a transport error raises
``InstagramCallError`` so the caller keeps the last snapshot.
"""

from __future__ import annotations

import asyncio

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_API_REQUEST_FAILED,
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
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
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import guard_graph
from rag_backend.modules.autopilot.insights_constants import (
    FIELD_DATA,
    FIELD_METRIC,
    FIELD_NAME,
    FIELD_TOTAL_VALUE,
    FIELD_VALUE,
    FIELD_VALUES,
    GRAPH_PATH_MEDIA_INSIGHTS,
    INSIGHT_METRICS,
)

INSIGHTS_REQUEST_DEADLINE_SECONDS = 10.0


class GraphInsightsGateway:
    """``InsightsGateway`` over the Instagram Graph API."""

    def __init__(
        self, config: MetaInstagramPublisherConfig, client: httpx.AsyncClient
    ) -> None:
        self._config = config
        self._client = client

    async def media_insights(self, media_id: str) -> InsightMetrics:
        """The post's metrics; omitted or refused metrics are ``None``."""
        if not media_id.isdigit():
            return InsightMetrics()
        return await guard_graph(lambda: self._read_all(media_id))

    async def _read_all(self, media_id: str) -> InsightMetrics:
        try:
            values = await self._read(media_id, INSIGHT_METRICS)
        except InstagramGraphError as exc:
            if exc.transient:
                raise
            values = await self._read_one_by_one(media_id)
        return InsightMetrics.from_values(values)

    async def _read_one_by_one(self, media_id: str) -> dict[str, int]:
        values: dict[str, int] = {}
        for metric in INSIGHT_METRICS:
            try:
                values.update(await self._read(media_id, (metric,)))
            except InstagramGraphError as exc:
                if exc.transient:
                    raise
        return values

    async def _read(self, media_id: str, metrics: tuple[str, ...]) -> dict[str, int]:
        token = await self._config.token_provider.get()
        if not token or not self._config.ig_user_id:
            raise RuntimeError(ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED)
        url = self._config.graph_base.rstrip("/") + GRAPH_PATH_MEDIA_INSIGHTS.format(
            media_id=media_id
        )
        params = {FIELD_METRIC: ",".join(metrics), COOKIE_ACCESS_TOKEN: token}
        async with asyncio.timeout(INSIGHTS_REQUEST_DEADLINE_SECONDS):
            response = await self._client.get(url, params=params)
        try:
            if not response.is_success:
                raise error_from(response)
            return parse_insights(json_dict(response))
        except ValueError as exc:
            # A non-JSON body (a proxy or outage page): retry on a later read.
            raise InstagramGraphError(
                status_code=response.status_code,
                error_code=ERR_INSTAGRAM_API_REQUEST_FAILED,
                transient=True,
            ) from exc


def build_insights_gateway(
    settings: Settings, client: httpx.AsyncClient
) -> GraphInsightsGateway | None:
    """The Graph reader for the configured account, or None without one."""
    if not settings.meta_ig_user_id.strip():
        return None
    return GraphInsightsGateway(
        MetaInstagramPublisherConfig(
            ig_user_id=settings.meta_ig_user_id,
            graph_base=settings.meta_ig_graph_base,
            token_provider=token_provider_for(settings),
        ),
        client,
    )


def parse_insights(payload: dict[str, object]) -> dict[str, int]:
    """``{metric: value}`` from a Graph insights body; odd entries are skipped."""
    data = payload.get(FIELD_DATA)
    if not isinstance(data, list):
        return {}
    values: dict[str, int] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get(FIELD_NAME)
        value = _metric_value(item)
        if isinstance(name, str) and value is not None:
            values[name] = value
    return values


def _metric_value(item: dict[str, object]) -> int | None:
    """``values[0].value`` (lifetime media metrics) or ``total_value.value``."""
    total = item.get(FIELD_TOTAL_VALUE)
    if isinstance(total, dict):
        return _as_count(total.get(FIELD_VALUE))
    series = item.get(FIELD_VALUES)
    if isinstance(series, list) and series and isinstance(series[0], dict):
        return _as_count(series[0].get(FIELD_VALUE))
    return None


def _as_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


__all__ = ["GraphInsightsGateway", "build_insights_gateway", "parse_insights"]
