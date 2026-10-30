"""The dashboard's Instagram insights (ADR-0021 D11).

Each published post is served from its stored snapshot. A snapshot older than
six hours (or none) is read again from the Graph API, at most
``INSIGHTS_REFRESH_PER_REQUEST`` per request so the page stays fast; the rest
are refreshed on the next request. When Graph fails, or is not configured,
the last snapshot is kept and the row is flagged stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import structlog

from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.insights import (
    ConnectorStatusQuery,
    InsightMetrics,
    InsightsGateway,
    InsightSnapshot,
    InsightsReport,
    InsightsStore,
    PostInsightsRow,
    PublishedPost,
    build_report,
    connector_status,
    is_due,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.insights_constants import (
    CHANNEL_INSTAGRAM,
    INSIGHTS_POST_LIMIT,
    INSIGHTS_REFRESH_PER_REQUEST,
    LOG_INSIGHTS,
    LOG_REFRESH_FAILED,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class InsightsDependencies:
    """The store, the clock and the Graph gateway (None when unconfigured)."""

    store: InsightsStore
    clock: Clock
    gateway: InsightsGateway | None = None


@dataclass
class _Pass:
    """One request: the time, the Graph reads left and the first error code."""

    now: datetime
    budget: int
    saved: int = 0
    error_code: str | None = None


class InstagramInsightsService:
    """Rows for the newest published posts, refreshed when due."""

    def __init__(self, deps: InsightsDependencies) -> None:
        self._deps = deps

    async def report(self) -> InsightsReport:
        """One row per published post plus the KPI ratios and connector state."""
        posts = await self._deps.store.published_posts(INSIGHTS_POST_LIMIT)
        snapshots = await self._deps.store.snapshots([p.media_id for p in posts])
        state = _Pass(now=self._deps.clock.now(), budget=INSIGHTS_REFRESH_PER_REQUEST)
        rows = [
            await self._row(post, snapshots.get(post.media_id), state) for post in posts
        ]
        if state.saved:
            await self._deps.store.commit()
        return build_report(
            rows,
            connector=connector_status(
                ConnectorStatusQuery(
                    channel=CHANNEL_INSTAGRAM,
                    configured=self._deps.gateway is not None,
                    rows=rows,
                    now=state.now,
                    refresh_error=state.error_code,
                )
            ),
        )

    async def _row(
        self, post: PublishedPost, snapshot: InsightSnapshot | None, state: _Pass
    ) -> PostInsightsRow:
        due = is_due(snapshot, state.now)
        if not due:
            return _from_snapshot(post, snapshot, stale=False)
        gateway = self._deps.gateway
        if gateway is None or state.budget <= 0:
            return _from_snapshot(post, snapshot, stale=True)
        state.budget -= 1
        try:
            metrics = await gateway.media_insights(post.media_id)
        except InstagramCallError as exc:
            logger.warning(
                LOG_INSIGHTS,
                outcome=LOG_REFRESH_FAILED,
                media_id=post.media_id,
                error_code=exc.error_code,
            )
            if state.error_code is None:
                state.error_code = exc.error_code
            return _from_snapshot(post, snapshot, stale=True)
        fresh = InsightSnapshot(
            media_id=post.media_id, metrics=metrics, fetched_at=state.now
        )
        await self._deps.store.save(fresh)
        state.saved += 1
        return _from_snapshot(post, fresh, stale=False)


def _from_snapshot(
    post: PublishedPost, snapshot: InsightSnapshot | None, *, stale: bool
) -> PostInsightsRow:
    if snapshot is None:
        return PostInsightsRow(
            post=post, metrics=InsightMetrics(), fetched_at=None, stale=stale
        )
    return PostInsightsRow(
        post=post, metrics=snapshot.metrics, fetched_at=snapshot.fetched_at, stale=stale
    )


__all__ = ["InsightsDependencies", "InstagramInsightsService"]
