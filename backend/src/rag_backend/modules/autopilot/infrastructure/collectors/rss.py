"""RSS collector. One bad feed is skipped; the others are still returned."""

from __future__ import annotations

import structlog

from rag_backend.modules.autopilot.constants import (
    ANTHROPIC_NEWS_PATH,
    FEED_URL_ANTHROPIC,
    FEED_URL_GOOGLE_AI,
    FEED_URL_META_AI,
    FEED_URL_OPENAI,
    FEED_URL_VERGE_AI,
    LOG_UPSTREAM_SKIPPED,
    SOURCE_RSS,
)
from rag_backend.modules.autopilot.domain.signals import CollectWindow, Signal
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
    is_http_success,
)
from rag_backend.modules.autopilot.infrastructure.collectors.rss_parse import (
    FeedSpec,
    parse_feed,
)

logger = structlog.get_logger()

DEFAULT_FEEDS = (
    FeedSpec(url=FEED_URL_OPENAI),
    FeedSpec(url=FEED_URL_ANTHROPIC, path_contains=ANTHROPIC_NEWS_PATH),
    FeedSpec(url=FEED_URL_GOOGLE_AI),
    FeedSpec(url=FEED_URL_META_AI),
    FeedSpec(url=FEED_URL_VERGE_AI),
)


class RssCollector:
    """Read the configured feeds. A total failure raises; a partial one does not."""

    def __init__(
        self,
        http: HttpGetter,
        feeds: tuple[FeedSpec, ...] = DEFAULT_FEEDS,
    ) -> None:
        self._http = http
        self._feeds = feeds
        self._source = SOURCE_RSS

    def source_name(self) -> str:
        """Source id recorded when every feed fails."""
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Fetch each feed. Items from the feeds that answered are returned."""
        signals: list[Signal] = []
        failures = 0
        for spec in self._feeds:
            batch = await self._read(spec, window)
            if batch is None:
                failures += 1
                continue
            signals.extend(batch)
        if self._feeds and not signals and failures == len(self._feeds):
            raise UpstreamError
        return signals

    async def _read(self, spec: FeedSpec, window: CollectWindow) -> list[Signal] | None:
        try:
            response = await self._http.get(HttpGet(url=spec.url))
        except Exception:
            logger.warning(LOG_UPSTREAM_SKIPPED, source=SOURCE_RSS)
            return None
        if not is_http_success(response.status_code):
            logger.warning(LOG_UPSTREAM_SKIPPED, source=SOURCE_RSS)
            return None
        try:
            return parse_feed(response.text, spec, window)
        except Exception:
            logger.warning(LOG_UPSTREAM_SKIPPED, source=SOURCE_RSS)
            return None
