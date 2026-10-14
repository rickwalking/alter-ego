"""``ddgs`` text search, run off the event loop.

An empty result set is an empty list. The library raises when a query
matches nothing; that case is not a collector failure.
"""

from __future__ import annotations

import asyncio
from typing import cast

from rag_backend.modules.autopilot.constants import NO_RESULTS_MARK
from rag_backend.modules.autopilot.domain.ports import WebSearchHit, WebSearchQuery
from rag_backend.modules.autopilot.infrastructure.collectors.coerce import (
    as_mapping,
    as_str,
)

_KEY_HREF = "href"
_KEY_TITLE = "title"
_KEY_BODY = "body"


class DdgsWebSearch:
    """Production ``WebSearchClient``. Snippets only; this class does not fetch URLs."""

    def __init__(self) -> None:
        self.last_query: WebSearchQuery | None = None

    async def search(self, query: WebSearchQuery) -> list[WebSearchHit]:
        """Run ``DDGS.text`` in a worker thread."""
        self.last_query = query
        raw = await asyncio.to_thread(_search_sync, query)
        return _hits(raw)


def _search_sync(query: WebSearchQuery) -> list[object]:
    try:
        return _call_ddgs(query)
    except Exception as exc:
        if NO_RESULTS_MARK in str(exc):
            return []
        raise


def _call_ddgs(query: WebSearchQuery) -> list[object]:
    from ddgs import DDGS

    with DDGS() as client:
        found = client.text(
            query.text,
            max_results=query.max_results,
            timelimit=query.timelimit,
        )
    return [cast(object, item) for item in found]


def _hits(raw: list[object]) -> list[WebSearchHit]:
    hits: list[WebSearchHit] = []
    for item in raw:
        hit = _hit(item)
        if hit is not None:
            hits.append(hit)
    return hits


def _hit(item: object) -> WebSearchHit | None:
    mapping = as_mapping(item)
    if mapping is None:
        return None
    url = as_str(mapping.get(_KEY_HREF))
    if not url:
        return None
    return WebSearchHit(
        url=url,
        title=as_str(mapping.get(_KEY_TITLE)),
        snippet=as_str(mapping.get(_KEY_BODY)),
    )
