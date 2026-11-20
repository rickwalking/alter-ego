"""``GET /reels``: the account's Reels with metrics, rates and repost history.

Insight snapshots older than 6 h are read again, at most a fixed number per
request (missing ones first); the rest are returned ``stale``. Durations and
collaborators are probed once and cached. Reels with a live repost in the
exclusion window, and Reels that are themselves reposts, are hidden.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeVar

import structlog

from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightsGateway,
    InsightSnapshot,
    InsightsStore,
    is_due,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.reels import (
    LastRepost,
    ReelFacts,
    ReelItem,
    ReelMedia,
    ReelsBaseline,
    age_days,
    baseline,
    reel_rates,
    sort_items,
)
from rag_backend.modules.autopilot.domain.reels_query import ReelsQuery, encode_cursor
from rag_backend.modules.autopilot.domain.repost import RepostError, RepostProblem
from rag_backend.modules.autopilot.domain.repost_ports import (
    ReelFactsStore,
    ReelGateway,
    ReelProbe,
    RepostStore,
)
from rag_backend.modules.autopilot.ig_media_constants import (
    METRICS_REELS,
    PRODUCT_REELS,
)
from rag_backend.modules.autopilot.insights_constants import METRIC_FOLLOWS
from rag_backend.modules.autopilot.reels_constants import (
    FACTS_PROBE_PER_REQUEST,
    GRAPH_CONCURRENCY,
    INSIGHTS_REFRESH_PER_REQUEST,
    LOG_INSIGHTS_FAILED,
    LOG_REELS,
)
from rag_backend.modules.autopilot.repost_constants import (
    ERR_NOT_CONFIGURED,
    ERR_UNAVAILABLE,
    HTTP_UNAVAILABLE,
)

logger = structlog.get_logger()

REEL_METRICS: tuple[str, ...] = (*METRICS_REELS, METRIC_FOLLOWS)


@dataclass(frozen=True, kw_only=True)
class ReelsDeps:
    """Graph readers (None when unconfigured), caches and the clock."""

    reels: ReelGateway | None
    insights_gateway: InsightsGateway | None
    insights: InsightsStore
    facts: ReelFactsStore
    reposts: RepostStore
    probe: ReelProbe | None
    clock: Clock


@dataclass(frozen=True, kw_only=True)
class ReelsPage:
    """One page of ``GET /reels``."""

    items: tuple[ReelItem, ...]
    baseline: ReelsBaseline
    next_cursor: str | None
    generated_at: datetime


@dataclass(frozen=True, kw_only=True)
class _Window:
    reels: list[ReelMedia]
    now: datetime


class ReelsService:
    """Lists Reels the scout may repost."""

    def __init__(self, deps: ReelsDeps) -> None:
        self._deps = deps

    async def page(self, query: ReelsQuery) -> ReelsPage:
        """Sorted, filtered and paged Reels with a window baseline."""
        now = self._deps.clock.now()
        window = _Window(reels=await self._listed(query, now), now=now)
        ids = [reel.media_id for reel in window.reels]
        snapshots = await self._snapshots(window)
        facts = await self._facts(window)
        latest = await self._deps.reposts.latest_for(ids)
        known = _Known(snapshots=snapshots, facts=facts, latest=latest, now=now)
        items = [_item(reel, known) for reel in window.reels]
        hidden = await self._deps.reposts.hidden_media(_since(query, now))
        await self._deps.reposts.commit()
        visible = [item for item in items if item.media.media_id not in hidden]
        cut = _Cut(items=sort_items(visible, query.sort), base=baseline(items), now=now)
        return _paged(cut, query)

    async def _listed(self, query: ReelsQuery, now: datetime) -> list[ReelMedia]:
        gateway = self._deps.reels
        if gateway is None:
            raise _unavailable(ERR_NOT_CONFIGURED)
        try:
            reels = await gateway.list_reels(now - timedelta(days=query.max_age_days))
        except InstagramCallError:
            raise _unavailable(ERR_UNAVAILABLE) from None
        return [
            r
            for r in reels
            if r.product_type == PRODUCT_REELS
            and age_days(r.posted_at, now) >= query.min_age_days
        ]

    async def _snapshots(self, window: _Window) -> dict[str, InsightSnapshot]:
        ids = [reel.media_id for reel in window.reels]
        stored = await self._deps.insights.snapshots(ids)
        due = [i for i in ids if is_due(stored.get(i), window.now)]
        due.sort(key=lambda i: (i in stored, _fetched(stored.get(i))))
        fresh = await _bounded(
            due[:INSIGHTS_REFRESH_PER_REQUEST],
            lambda media_id: self._insights(media_id, window.now),
        )
        for snapshot in fresh:
            if snapshot is not None:
                await self._deps.insights.save(snapshot)
                stored[snapshot.media_id] = snapshot
        return stored

    async def _insights(self, media_id: str, now: datetime) -> InsightSnapshot | None:
        gateway = self._deps.insights_gateway
        if gateway is None:
            return None
        try:
            metrics = await gateway.media_insights(media_id, REEL_METRICS)
        except InstagramCallError as exc:
            logger.warning(LOG_REELS, outcome=LOG_INSIGHTS_FAILED, code=exc.error_code)
            return None
        return InsightSnapshot(
            media_id=media_id,
            metrics=metrics,
            fetched_at=now,
            written=frozenset(REEL_METRICS),
        )

    async def _facts(self, window: _Window) -> dict[str, ReelFacts]:
        ids = [reel.media_id for reel in window.reels]
        known = await self._deps.facts.facts(ids)
        missing = [reel for reel in window.reels if reel.media_id not in known]
        probed = await _bounded(
            missing[:FACTS_PROBE_PER_REQUEST],
            lambda reel: self._probe(reel, window.now),
        )
        for facts in probed:
            if facts is not None:
                await self._deps.facts.save_facts(facts)
                known[facts.media_id] = facts
        return known

    async def _probe(self, reel: ReelMedia, now: datetime) -> ReelFacts | None:
        probe, gateway = self._deps.probe, self._deps.reels
        duration = None
        if probe is not None and reel.video_url:
            duration = await probe.duration(reel.video_url)
        try:
            names = (
                () if gateway is None else await gateway.collaborators(reel.media_id)
            )
        except InstagramCallError:
            return None
        return ReelFacts(
            media_id=reel.media_id,
            duration_s=duration,
            collaborators=names,
            probed_at=now,
        )


_T = TypeVar("_T")
_R = TypeVar("_R")


async def _bounded(
    values: Sequence[_T], call: Callable[[_T], Awaitable[_R]]
) -> list[_R]:
    gate = asyncio.Semaphore(GRAPH_CONCURRENCY)

    async def one(value: _T) -> _R:
        async with gate:
            return await call(value)

    return list(await asyncio.gather(*(one(value) for value in values)))


def _since(query: ReelsQuery, now: datetime) -> datetime | None:
    """No window (only reposts themselves are hidden) when the days are 0."""
    if query.exclude_reposted_days == 0:
        return None
    return now - timedelta(days=query.exclude_reposted_days)


def _fetched(snapshot: InsightSnapshot | None) -> float:
    return 0.0 if snapshot is None else snapshot.fetched_at.timestamp()


@dataclass(frozen=True, kw_only=True)
class _Known:
    snapshots: dict[str, InsightSnapshot]
    facts: dict[str, ReelFacts]
    latest: dict[str, LastRepost]
    now: datetime


def _item(reel: ReelMedia, known: _Known) -> ReelItem:
    snapshot = known.snapshots.get(reel.media_id)
    facts = known.facts.get(reel.media_id)
    metrics = InsightMetrics() if snapshot is None else snapshot.metrics
    duration = None if facts is None else facts.duration_s
    return ReelItem(
        media=reel,
        facts=facts,
        metrics=metrics,
        rates=reel_rates(metrics, duration),
        stale=is_due(snapshot, known.now),
        age_days=age_days(reel.posted_at, known.now),
        last_repost=known.latest.get(reel.media_id),
    )


@dataclass(frozen=True, kw_only=True)
class _Cut:
    items: list[ReelItem]
    base: ReelsBaseline
    now: datetime


def _paged(cut: _Cut, query: ReelsQuery) -> ReelsPage:
    end = query.offset + query.limit
    return ReelsPage(
        items=tuple(cut.items[query.offset : end]),
        baseline=cut.base,
        next_cursor=encode_cursor(end) if end < len(cut.items) else None,
        generated_at=cut.now,
    )


def _unavailable(code: str) -> RepostError:
    return RepostError(RepostProblem(code=code, status=HTTP_UNAVAILABLE))


__all__ = ["REEL_METRICS", "ReelsDeps", "ReelsPage", "ReelsService"]
