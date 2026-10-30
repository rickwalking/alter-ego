"""SQLAlchemy ``InsightsStore`` (ADR-0021 D11).

Published posts come from the two places that store an Instagram media id:
autopilot runs and the manual-publish ledger. The carousel topic is read
through a lightweight table clause (the autopilot module never imports the
carousel ORM). Snapshots live in ``instagram_post_insights``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import column, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.insights import (
    InsightMetrics,
    InsightSnapshot,
    PublishedPost,
)
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware
from rag_backend.modules.autopilot.insights_constants import (
    COLUMN_AVG_WATCH_TIME,
    COLUMN_TOTAL_WATCH_TIME,
    METRIC_AVG_WATCH_TIME,
    METRIC_COMMENTS,
    METRIC_FOLLOWS,
    METRIC_LIKES,
    METRIC_PROFILE_VISITS,
    METRIC_REACH,
    METRIC_SAVED,
    METRIC_SHARES,
    METRIC_TOTAL_INTERACTIONS,
    METRIC_TOTAL_WATCH_TIME,
    METRIC_VIEWS,
)

_CAROUSELS = table("carousel_projects", column("id"), column("topic"))
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class SqlInsightsStore:
    """Reads published posts; one snapshot row per media id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def published_posts(self, limit: int) -> list[PublishedPost]:
        """Newest first, one per media id, from runs and the manual ledger."""
        found = [*await self._run_posts(limit), *await self._manual_posts(limit)]
        found.sort(key=lambda item: item[0], reverse=True)
        posts: dict[str, PublishedPost] = {}
        for _, post in found:
            posts.setdefault(post.media_id, post)
        return list(posts.values())[:limit]

    async def snapshots(self, media_ids: Sequence[str]) -> dict[str, InsightSnapshot]:
        """The stored snapshot per media id."""
        if not media_ids:
            return {}
        rows = await self._session.scalars(
            select(InstagramPostInsightsModel).where(
                InstagramPostInsightsModel.media_id.in_(list(media_ids))
            )
        )
        return {row.media_id: _snapshot(row) for row in rows}

    async def save(self, snapshot: InsightSnapshot) -> None:
        """Insert or replace the media id's snapshot (flushed, not committed)."""
        row = await self._session.get(InstagramPostInsightsModel, snapshot.media_id)
        if row is None:
            row = InstagramPostInsightsModel(
                media_id=snapshot.media_id, fetched_at=snapshot.fetched_at
            )
            self._session.add(row)
        _write(row, snapshot)
        await self._session.flush()

    async def commit(self) -> None:
        """Commit the saved snapshots."""
        await self._session.commit()

    async def _run_posts(self, limit: int) -> list[tuple[datetime, PublishedPost]]:
        run = AutopilotRunModel
        result = await self._session.execute(
            select(
                run.ig_post_id,
                run.carousel_project_id,
                run.ig_permalink,
                run.updated_at,
                _CAROUSELS.c.topic,
            )
            .outerjoin(_CAROUSELS, _CAROUSELS.c.id == run.carousel_project_id)
            .where(run.ig_post_id.is_not(None))
            .order_by(run.updated_at.desc())
            .limit(limit)
        )
        return [_published(row) for row in result.all()]

    async def _manual_posts(self, limit: int) -> list[tuple[datetime, PublishedPost]]:
        manual = ManualPublishModel
        result = await self._session.execute(
            select(
                manual.ig_post_id,
                manual.carousel_project_id,
                manual.ig_permalink,
                manual.claimed_at,
                _CAROUSELS.c.topic,
            )
            .outerjoin(_CAROUSELS, _CAROUSELS.c.id == manual.carousel_project_id)
            .where(manual.ig_post_id.is_not(None))
            .order_by(manual.claimed_at.desc())
            .limit(limit)
        )
        return [_published(row) for row in result.all()]


def _published(row: Sequence[object]) -> tuple[datetime, PublishedPost]:
    media_id, project_id, permalink, at, topic = row
    when = aware(at) if isinstance(at, datetime) else None
    return (
        when or _EPOCH,
        PublishedPost(
            media_id=str(media_id),
            carousel_project_id=str(project_id) if project_id else None,
            permalink=permalink if isinstance(permalink, str) else None,
            topic=topic if isinstance(topic, str) else None,
        ),
    )


_MetricRead = Callable[[InsightMetrics], int | None]

_READ: dict[str, _MetricRead] = {
    METRIC_VIEWS: lambda metrics: metrics.views,
    METRIC_REACH: lambda metrics: metrics.reach,
    METRIC_SAVED: lambda metrics: metrics.saved,
    METRIC_SHARES: lambda metrics: metrics.shares,
    METRIC_FOLLOWS: lambda metrics: metrics.follows,
    METRIC_PROFILE_VISITS: lambda metrics: metrics.profile_visits,
    METRIC_TOTAL_INTERACTIONS: lambda metrics: metrics.total_interactions,
    METRIC_LIKES: lambda metrics: metrics.likes,
    METRIC_COMMENTS: lambda metrics: metrics.comments,
    METRIC_AVG_WATCH_TIME: lambda metrics: metrics.avg_watch_time_ms,
    METRIC_TOTAL_WATCH_TIME: lambda metrics: metrics.total_watch_time_ms,
}

_COLUMN: dict[str, str] = {
    METRIC_VIEWS: METRIC_VIEWS,
    METRIC_REACH: METRIC_REACH,
    METRIC_SAVED: METRIC_SAVED,
    METRIC_SHARES: METRIC_SHARES,
    METRIC_FOLLOWS: METRIC_FOLLOWS,
    METRIC_PROFILE_VISITS: METRIC_PROFILE_VISITS,
    METRIC_TOTAL_INTERACTIONS: METRIC_TOTAL_INTERACTIONS,
    METRIC_LIKES: METRIC_LIKES,
    METRIC_COMMENTS: METRIC_COMMENTS,
    METRIC_AVG_WATCH_TIME: COLUMN_AVG_WATCH_TIME,
    METRIC_TOTAL_WATCH_TIME: COLUMN_TOTAL_WATCH_TIME,
}


def _snapshot(row: InstagramPostInsightsModel) -> InsightSnapshot:
    return InsightSnapshot(
        media_id=row.media_id,
        metrics=InsightMetrics(
            views=row.views,
            reach=row.reach,
            saved=row.saved,
            shares=row.shares,
            follows=row.follows,
            profile_visits=row.profile_visits,
            total_interactions=row.total_interactions,
            likes=row.likes,
            comments=row.comments,
            avg_watch_time_ms=row.avg_watch_time_ms,
            total_watch_time_ms=row.total_watch_time_ms,
        ),
        fetched_at=aware(row.fetched_at) or _EPOCH,
    )


def _write(row: InstagramPostInsightsModel, snapshot: InsightSnapshot) -> None:
    for name in snapshot.written:
        _assign(row, name, _READ[name](snapshot.metrics) if name in _READ else None)
    row.fetched_at = snapshot.fetched_at


def _assign(row: InstagramPostInsightsModel, name: str, value: int | None) -> None:
    column_name = _COLUMN.get(name)
    if column_name is None:
        return
    setattr(row, column_name, value)


__all__ = ["SqlInsightsStore"]
