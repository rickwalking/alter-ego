"""Autopilot Instagram insights: account media, rates and baselines.

The media list is cached for 30 minutes. Snapshots older than six hours are
read again, at most ten Graph reads per request. A failure keeps the last
snapshot and marks the row stale.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

import structlog

from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.ig_media import (
    IgInsightItem,
    IgInsightsReport,
    IgMedia,
    IgMediaStore,
    MediaListCommand,
    MediaListGateway,
    MediaProject,
    OpenBoost,
    ResolvedIgQuery,
    TimeWindow,
    age_hours,
    baseline_window,
    baselines,
    empty_baselines,
    metrics_for,
    rates_for,
)
from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightsGateway,
    InsightSnapshot,
    InsightsStore,
    is_due,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.ig_media_constants import (
    LOG_IG_MEDIA,
    LOG_LIST_FAILED,
)
from rag_backend.modules.autopilot.insights_constants import (
    INSIGHTS_REFRESH_PER_REQUEST,
    LOG_REFRESH_FAILED,
)

logger = structlog.get_logger()


class OpenBoostLookup(Protocol):
    """Latest non-terminal boost request per media id."""

    async def open_for(self, media_ids: tuple[str, ...]) -> dict[str, OpenBoost]:
        """Absent ids have no open boost."""
        ...


@dataclass(frozen=True, kw_only=True)
class IgInsightsDependencies:
    """Stores, clock and Graph gateways. Gateways are None when unconfigured."""

    media: IgMediaStore
    insights: InsightsStore
    clock: Clock
    media_gateway: MediaListGateway | None = None
    insights_gateway: InsightsGateway | None = None
    boosts: OpenBoostLookup | None = None


@dataclass
class _Listed:
    items: list[IgMedia]
    truncated: bool
    changed: bool


@dataclass(frozen=True, kw_only=True)
class _PagePass:
    page: list[IgMedia]
    now: datetime
    oldest_first: bool


@dataclass
class _RowQuery:
    item: IgMedia
    snapshot: InsightSnapshot | None
    refreshing: frozenset[str]
    now: datetime


class IgInsightsService:
    """One insights page for the autopilot key."""

    def __init__(self, deps: IgInsightsDependencies) -> None:
        self._deps = deps

    async def report(self, query: ResolvedIgQuery) -> IgInsightsReport:
        """Media in the window, newest first, plus per-type baselines."""
        now = self._deps.clock.now()
        if self._deps.media_gateway is None:
            return _empty(now)
        listed = await self._listed(query, now)
        page = _select(listed.items, query)
        rows, saved = await self._rows(
            _PagePass(page=page, now=now, oldest_first=query.refresh)
        )
        samples = await self._deps.media.baseline_samples(baseline_window(now))
        if listed.changed or saved:
            await self._deps.media.commit()
        return IgInsightsReport(
            items=tuple(rows),
            baseline=baselines(samples),
            next_until=_next_until(page, query.limit),
            configured=True,
            list_truncated=listed.truncated,
            generated_at=now,
        )

    async def _listed(self, query: ResolvedIgQuery, now: datetime) -> _Listed:
        fresh = await self._deps.media.list_is_fresh(now)
        if fresh and not query.refresh:
            return _Listed(
                items=await self._window(query), truncated=False, changed=False
            )
        gateway = self._deps.media_gateway
        if gateway is None:
            return _Listed(items=[], truncated=False, changed=False)
        try:
            result = await gateway.list_media(MediaListCommand(since=query.since))
        except InstagramCallError as exc:
            logger.warning(
                LOG_IG_MEDIA, outcome=LOG_LIST_FAILED, error_code=exc.error_code
            )
            return _Listed(
                items=await self._window(query), truncated=False, changed=False
            )
        await self._deps.media.upsert(result.items, now)
        return _Listed(
            items=await self._window(query),
            truncated=result.truncated,
            changed=True,
        )

    async def _window(self, query: ResolvedIgQuery) -> list[IgMedia]:
        return await self._deps.media.in_window(
            TimeWindow(start=query.since, end=query.until)
        )

    async def _rows(self, command: _PagePass) -> tuple[list[IgInsightItem], int]:
        page = command.page
        ids = [item.media_id for item in page]
        snapshots = await self._deps.insights.snapshots(ids)
        refreshing = _refresh_ids(page, snapshots, command)
        rows: list[IgInsightItem] = []
        saved = 0
        projects = await self._deps.media.projects(ids)
        for item in page:
            row, wrote = await self._row(
                _RowQuery(
                    item=item,
                    snapshot=snapshots.get(item.media_id),
                    refreshing=refreshing,
                    now=command.now,
                )
            )
            rows.append(_with_project(row, projects.get(item.media_id)))
            saved += wrote
        return await self._attach_boosts(rows, tuple(ids)), saved

    async def _row(self, query: _RowQuery) -> tuple[IgInsightItem, int]:
        if query.item.media_id not in query.refreshing:
            stale = is_due(query.snapshot, query.now)
            return _from_snapshot(_seen(query, query.snapshot, stale=stale)), 0
        gateway = self._deps.insights_gateway
        if gateway is None:
            return _from_snapshot(_seen(query, query.snapshot, stale=True)), 0
        requested = metrics_for(query.item.media_product_type)
        try:
            metrics = await gateway.media_insights(query.item.media_id, requested)
        except InstagramCallError as exc:
            logger.warning(
                LOG_IG_MEDIA,
                outcome=LOG_REFRESH_FAILED,
                media_id=query.item.media_id,
                error_code=exc.error_code,
            )
            return _from_snapshot(_seen(query, query.snapshot, stale=True)), 0
        fresh = InsightSnapshot(
            media_id=query.item.media_id,
            metrics=metrics,
            fetched_at=query.now,
            written=frozenset(requested),
        )
        await self._deps.insights.save(fresh)
        return _from_snapshot(_seen(query, fresh, stale=False)), 1

    async def _attach_boosts(
        self, rows: list[IgInsightItem], media_ids: tuple[str, ...]
    ) -> list[IgInsightItem]:
        lookup = self._deps.boosts
        if lookup is None:
            return rows
        found = await lookup.open_for(media_ids)
        return [_with_boost(row, found.get(row.media.media_id)) for row in rows]


def _select(items: list[IgMedia], query: ResolvedIgQuery) -> list[IgMedia]:
    matched = [item for item in items if _matches(item, query)]
    return matched[: query.limit]


def _matches(item: IgMedia, query: ResolvedIgQuery) -> bool:
    type_ok = query.media_type is None or item.media_type == query.media_type
    product_ok = (
        query.product_type is None or item.media_product_type == query.product_type
    )
    return type_ok and product_ok


def _refresh_ids(
    page: list[IgMedia],
    snapshots: dict[str, InsightSnapshot],
    command: _PagePass,
) -> frozenset[str]:
    due = [item for item in page if is_due(snapshots.get(item.media_id), command.now)]
    due.sort(key=lambda item: item.posted_at, reverse=not command.oldest_first)
    chosen = due[:INSIGHTS_REFRESH_PER_REQUEST]
    return frozenset(item.media_id for item in chosen)


def _next_until(page: list[IgMedia], limit: int) -> datetime | None:
    if len(page) < limit or not page:
        return None
    return page[-1].posted_at


@dataclass(frozen=True, kw_only=True)
class _Seen:
    item: IgMedia
    snapshot: InsightSnapshot | None
    now: datetime
    stale: bool


def _seen(query: _RowQuery, snapshot: InsightSnapshot | None, *, stale: bool) -> _Seen:
    return _Seen(item=query.item, snapshot=snapshot, now=query.now, stale=stale)


def _from_snapshot(seen: _Seen) -> IgInsightItem:
    metrics = seen.snapshot.metrics if seen.snapshot is not None else _blank()
    fetched = seen.snapshot.fetched_at if seen.snapshot is not None else None
    return IgInsightItem(
        media=seen.item,
        metrics=metrics,
        rates=rates_for(metrics),
        fetched_at=fetched,
        stale=seen.stale,
        age_hours=age_hours(seen.item.posted_at, seen.now),
        project=None,
    )


def _blank() -> InsightMetrics:
    return InsightMetrics()


def _with_project(item: IgInsightItem, project: MediaProject | None) -> IgInsightItem:
    if project is None:
        return item
    return IgInsightItem(
        media=item.media,
        metrics=item.metrics,
        rates=item.rates,
        fetched_at=item.fetched_at,
        stale=item.stale,
        age_hours=item.age_hours,
        project=project,
        boost=item.boost,
    )


def _with_boost(item: IgInsightItem, boost: OpenBoost | None) -> IgInsightItem:
    if boost is None:
        return item
    return replace(item, boost=boost)


def _empty(now: datetime) -> IgInsightsReport:
    return IgInsightsReport(
        items=(),
        baseline=empty_baselines(),
        next_until=None,
        configured=False,
        list_truncated=False,
        generated_at=now,
    )


__all__ = ["IgInsightsDependencies", "IgInsightsService"]
