"""Bluesky trends from the public AppView. No auth."""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import (
    BSKY_ORIGIN,
    BSKY_PARAM_LIMIT,
    BSKY_TREND_LIMIT,
    BSKY_TRENDS_URL,
    SCHEME_HTTPS,
    SOURCE_BLUESKY,
)
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)
from rag_backend.modules.autopilot.infrastructure.collectors.coerce import (
    as_int,
    as_list,
    as_mapping,
    as_str,
    loads_json,
)
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
    is_http_success,
)
from rag_backend.modules.autopilot.infrastructure.collectors.timestamps import (
    parse_timestamp,
)

_KEY_TRENDS = "trends"
_KEY_TOPIC = "topic"
_KEY_DISPLAY = "displayName"
_KEY_LINK = "link"
_KEY_STARTED = "startedAt"
_KEY_POST_COUNT = "postCount"
_KEY_DESCRIPTION = "description"
_PATH_PREFIX = "/"


class BlueskyTrendsCollector:
    """Current Bluesky trends. Relative ``link`` values are joined to bsky.app."""

    def __init__(self, http: HttpGetter) -> None:
        self._http = http
        self._source = SOURCE_BLUESKY

    def source_name(self) -> str:
        """Source id recorded when this collector fails."""
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Return the trend list. ``window`` is accepted to satisfy ``Collector``."""
        del window
        response = await self._http.get(
            HttpGet(
                url=BSKY_TRENDS_URL,
                params=((BSKY_PARAM_LIMIT, BSKY_TREND_LIMIT),),
            )
        )
        if not is_http_success(response.status_code):
            raise UpstreamError
        parsed = loads_json(response.text)
        if parsed is None:
            raise UpstreamError
        return signals_from_bluesky(parsed)


def signals_from_bluesky(payload: object) -> list[Signal]:
    """Map a ``getTrends`` body. Trends without a link or a start time are skipped."""
    mapping = as_mapping(payload)
    if mapping is None:
        return []
    signals: list[Signal] = []
    for item in as_list(mapping.get(_KEY_TRENDS)):
        signal = _trend(item)
        if signal is not None:
            signals.append(signal)
    return signals


def _trend(item: object) -> Signal | None:
    mapping = as_mapping(item)
    if mapping is None:
        return None
    url = absolute_bsky_url(as_str(mapping.get(_KEY_LINK)))
    posted_at = parse_timestamp(as_str(mapping.get(_KEY_STARTED)))
    if not url or posted_at is None:
        return None
    title = as_str(mapping.get(_KEY_DISPLAY)) or as_str(mapping.get(_KEY_TOPIC))
    text = as_str(mapping.get(_KEY_DESCRIPTION)) or title
    return signal_from(
        SignalDraft(
            source=SignalSource.BLUESKY,
            url=url,
            title=title,
            text=text,
            posted_at=posted_at,
            score_hint=as_int(mapping.get(_KEY_POST_COUNT)),
        )
    )


def absolute_bsky_url(link: str) -> str:
    """Prefix a relative AppView path. Absolute https links pass through."""
    if link.startswith(f"{SCHEME_HTTPS}://"):
        return link
    if link.startswith(_PATH_PREFIX):
        return f"{BSKY_ORIGIN}{link}"
    return ""
