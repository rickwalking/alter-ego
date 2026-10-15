"""SQLAlchemy ``InsightsStore`` (AE-0378, ADR-0021 D11).

Published posts come from the two places that store an Instagram media id:
autopilot runs and the manual-publish ledger. The carousel topic is read
through a lightweight table clause (the autopilot module never imports the
carousel ORM). Snapshots live in ``instagram_post_insights``.
"""

from __future__ import annotations

from collections.abc import Sequence
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
        ),
        fetched_at=aware(row.fetched_at) or _EPOCH,
    )


def _write(row: InstagramPostInsightsModel, snapshot: InsightSnapshot) -> None:
    metrics = snapshot.metrics
    row.views = metrics.views
    row.reach = metrics.reach
    row.saved = metrics.saved
    row.shares = metrics.shares
    row.follows = metrics.follows
    row.profile_visits = metrics.profile_visits
    row.total_interactions = metrics.total_interactions
    row.fetched_at = snapshot.fetched_at


__all__ = ["SqlInsightsStore"]
