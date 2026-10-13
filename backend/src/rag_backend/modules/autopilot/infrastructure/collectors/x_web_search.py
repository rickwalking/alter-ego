"""X signals from search-engine snippets (architecture §5.1).

Queries are spaced 2-5 seconds apart and capped at six per run. Only
recent status URLs are kept. The same post seen in several queries gets
a higher ``score_hint``. The resolver is never required: a miss keeps
the snippet.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import structlog
from rag_backend.modules.autopilot.domain.snowflake import posted_at_from_snowflake

from rag_backend.modules.autopilot.constants import (
    LOG_UPSTREAM_SKIPPED,
    SOURCE_X_SEARCH,
    X_MAX_QUERIES_PER_RUN,
    X_RESOLVE_TIMEOUT_SECONDS,
    X_SEARCH_MAX_RESULTS,
    X_SEARCH_QUERIES,
    X_SEARCH_TIMELIMIT,
)
from rag_backend.modules.autopilot.domain.ports import (
    WebSearchClient,
    WebSearchHit,
    WebSearchQuery,
    XPostResolver,
)
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)
from rag_backend.modules.autopilot.domain.x_status import (
    XStatusTarget,
    is_recent_status,
    parse_status_url,
)
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError

logger = structlog.get_logger()


class QueryPause(Protocol):
    """Sleep between search queries. Tests record the delay and return."""

    async def pause(self, seconds: float) -> None:
        """Wait ``seconds`` before the next query."""
        ...


class SpacingJitter(Protocol):
    """Draw the 2-5 second gap between queries."""

    def seconds(self) -> float:
        """Return the next gap."""
        ...


@dataclass(frozen=True, kw_only=True)
class XWebSearchDependencies:
    """Search, resolver, and pacing for one X collection."""

    search: WebSearchClient
    resolver: XPostResolver
    pause: QueryPause
    jitter: SpacingJitter
    queries: tuple[str, ...] = X_SEARCH_QUERIES


@dataclass
class _Group:
    hit: WebSearchHit
    target: XStatusTarget
    posted_at: datetime
    queries: set[str] = field(default_factory=set)


class XWebSearchCollector:
    """Collect recent X status posts from ``ddgs`` snippets."""

    def __init__(self, deps: XWebSearchDependencies) -> None:
        self._deps = deps
        self._source = SOURCE_X_SEARCH

    def source_name(self) -> str:
        """Source id recorded when this collector fails."""
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Search, filter, cluster, then optionally enrich. Snippets survive a miss."""
        groups = await self._search_all(window)
        signals: list[Signal] = []
        for group in groups.values():
            signal = await self._signal(group)
            if signal is not None:
                signals.append(signal)
        return signals

    async def _search_all(self, window: CollectWindow) -> dict[str, _Group]:
        groups: dict[str, _Group] = {}
        queries = self._deps.queries[:X_MAX_QUERIES_PER_RUN]
        failures = 0
        for index, query in enumerate(queries):
            if index:
                await self._deps.pause.pause(self._deps.jitter.seconds())
            hits = await self._search_one(query)
            if hits is None:
                failures += 1
                continue
            _absorb(
                _AbsorbCommand(
                    groups=groups,
                    hits=hits,
                    query=query,
                    window=window,
                )
            )
        if queries and failures == len(queries):
            raise UpstreamError
        return groups

    async def _search_one(self, query: str) -> list[WebSearchHit] | None:
        request = WebSearchQuery(
            text=query,
            timelimit=X_SEARCH_TIMELIMIT,
            max_results=X_SEARCH_MAX_RESULTS,
        )
        try:
            return await self._deps.search.search(request)
        except Exception:
            logger.warning(LOG_UPSTREAM_SKIPPED, source=SOURCE_X_SEARCH)
            return None

    async def _signal(self, group: _Group) -> Signal | None:
        text = await self._enriched(group)
        return signal_from(
            SignalDraft(
                source=SignalSource.X_SEARCH,
                url=group.target.canonical_url,
                title=group.hit.title,
                text=text,
                posted_at=group.posted_at,
                handle=group.target.handle,
                score_hint=len(group.queries),
            )
        )

    async def _enriched(self, group: _Group) -> str:
        try:
            resolved = await asyncio.wait_for(
                self._deps.resolver.resolve(group.target),
                timeout=X_RESOLVE_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.warning(LOG_UPSTREAM_SKIPPED, source=SOURCE_X_SEARCH)
            return group.hit.snippet
        if resolved is None or not resolved.strip():
            return group.hit.snippet
        return resolved


@dataclass(kw_only=True)
class _AbsorbCommand:
    groups: dict[str, _Group]
    hits: list[WebSearchHit]
    query: str
    window: CollectWindow


def _absorb(command: _AbsorbCommand) -> None:
    for hit in command.hits:
        _absorb_one(command, hit)


def _absorb_one(command: _AbsorbCommand, hit: WebSearchHit) -> None:
    target = parse_status_url(hit.url)
    if target is None:
        return
    posted_at = posted_at_from_snowflake(int(target.status_id))
    if not is_recent_status(posted_at, command.window.as_of):
        return
    existing = command.groups.get(target.canonical_url)
    if existing is None:
        command.groups[target.canonical_url] = _Group(
            hit=hit,
            target=target,
            posted_at=posted_at,
            queries={command.query},
        )
        return
    existing.queries.add(command.query)
