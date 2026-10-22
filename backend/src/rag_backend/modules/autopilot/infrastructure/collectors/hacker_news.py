"""Hacker News stories from the Algolia search API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from rag_backend.modules.autopilot.constants import (
    HN_FILTER_CREATED,
    HN_FILTER_POINTS,
    HN_ITEM_URL_PREFIX,
    HN_LOOKBACK_HOURS,
    HN_MIN_POINTS,
    HN_PARAM_NUMERIC_FILTERS,
    HN_PARAM_QUERY,
    HN_PARAM_TAGS,
    HN_SEARCH_QUERIES,
    HN_SEARCH_URL,
    HN_TAG_STORY,
    SOURCE_HN,
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
)
from rag_backend.modules.autopilot.infrastructure.collectors.fetch_json import (
    fetch_json,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
)
from rag_backend.modules.autopilot.infrastructure.collectors.timestamps import (
    parse_timestamp,
)

_KEY_HITS = "hits"
_KEY_URL = "url"
_KEY_TITLE = "title"
_KEY_POINTS = "points"
_KEY_OBJECT_ID = "objectID"
_KEY_CREATED = "created_at"
_KEY_AUTHOR = "author"
_KEY_STORY_TEXT = "story_text"


class HackerNewsCollector:
    """Stories above the point floor inside the lookback window."""

    def __init__(self, http: HttpGetter) -> None:
        self._http = http
        self._source = SOURCE_HN

    def source_name(self) -> str:
        """Source id recorded when this collector fails."""
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Query each keyword and concatenate the hits."""
        batches = await asyncio.gather(
            *(self._query(keyword, window) for keyword in HN_SEARCH_QUERIES)
        )
        signals: list[Signal] = []
        for batch in batches:
            signals.extend(batch)
        return signals

    async def _query(self, keyword: str, window: CollectWindow) -> list[Signal]:
        payload = await self._payload(keyword, window)
        return signals_from_hn(payload, window)

    async def _payload(self, keyword: str, window: CollectWindow) -> object:
        return await fetch_json(
            self._http,
            HttpGet(url=HN_SEARCH_URL, params=_params(keyword, window)),
        )


def signals_from_hn(payload: object, window: CollectWindow) -> list[Signal]:
    """Map an Algolia search body to signals. Low-point and stale hits are dropped."""
    mapping = as_mapping(payload)
    if mapping is None:
        return []
    cutoff = window.as_of - timedelta(hours=HN_LOOKBACK_HOURS)
    signals: list[Signal] = []
    for item in as_list(mapping.get(_KEY_HITS)):
        signal = _story(item, cutoff)
        if signal is not None:
            signals.append(signal)
    return signals


def _params(keyword: str, window: CollectWindow) -> tuple[tuple[str, str], ...]:
    cutoff = window.as_of - timedelta(hours=HN_LOOKBACK_HOURS)
    created_after = int(cutoff.timestamp())
    filters = f"{HN_FILTER_POINTS}>{HN_MIN_POINTS},{HN_FILTER_CREATED}>{created_after}"
    return (
        (HN_PARAM_TAGS, HN_TAG_STORY),
        (HN_PARAM_QUERY, keyword),
        (HN_PARAM_NUMERIC_FILTERS, filters),
    )


def _story(item: object, cutoff: datetime) -> Signal | None:
    mapping = as_mapping(item)
    if mapping is None:
        return None
    points = as_int(mapping.get(_KEY_POINTS))
    if points is None or points <= HN_MIN_POINTS:
        return None
    posted_at = parse_timestamp(as_str(mapping.get(_KEY_CREATED)))
    if posted_at is None or posted_at <= cutoff:
        return None
    url = _story_url(mapping)
    title = as_str(mapping.get(_KEY_TITLE))
    text = as_str(mapping.get(_KEY_STORY_TEXT)) or title
    return signal_from(
        SignalDraft(
            source=SignalSource.HN,
            url=url,
            title=title,
            text=text,
            posted_at=posted_at,
            handle=_handle(mapping),
            score_hint=points,
        )
    )


def _handle(mapping: dict[str, object]) -> str | None:
    author = as_str(mapping.get(_KEY_AUTHOR))
    if not author:
        return None
    return author


def _story_url(mapping: dict[str, object]) -> str:
    url = as_str(mapping.get(_KEY_URL))
    if url:
        return url
    object_id = as_str(mapping.get(_KEY_OBJECT_ID))
    if not object_id:
        return ""
    return f"{HN_ITEM_URL_PREFIX}{object_id}"
