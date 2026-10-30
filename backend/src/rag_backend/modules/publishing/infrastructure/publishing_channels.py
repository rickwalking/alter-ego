"""Channel-pluggable publishing counters for the editorial analytics.

Each counter lists the publish events of one channel and this module
aggregates them into per-channel totals and weekly velocity. A future
channel (LinkedIn, TikTok) slots in by adding its counter to
``CHANNEL_COUNTERS`` — the aggregation never changes.

The carousel counter reads the publish ledgers through lightweight
``table()`` clauses rather than importing the autopilot ORM: the autopilot
module keeps its internals private, and it uses the same pattern the other
way around (``SqlInsightsStore`` reads ``carousel_projects`` through a
``table()`` clause).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import DateTime, column, func, select, table, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import CompoundSelect, Select

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.modules.autopilot.constants import (
    CAROUSEL_PROJECTS_TABLE,
    TABLE_AUTOPILOT_RUNS,
)
from rag_backend.modules.autopilot.recovery_constants import (
    TABLE_MANUAL_PUBLISHES,
)
from rag_backend.modules.publishing.constants import (
    CHANNEL_BLOG,
    CHANNEL_CAROUSEL,
)
from rag_backend.modules.publishing.domain.projections import (
    AnalyticsVelocityWeek,
    ChannelPublishing,
)

_WEEK = timedelta(days=7)
_MONTH = timedelta(days=30)

_CAROUSELS = table(
    CAROUSEL_PROJECTS_TABLE,
    column("id"),
    column("owner_id"),
)
_RUNS = table(
    TABLE_AUTOPILOT_RUNS,
    column("carousel_project_id"),
    column("ig_post_id"),
    column("updated_at", DateTime(timezone=True)),
)
_MANUAL = table(
    TABLE_MANUAL_PUBLISHES,
    column("carousel_project_id"),
    column("ig_post_id"),
    column("claimed_at", DateTime(timezone=True)),
)


@dataclass(frozen=True, kw_only=True)
class ChannelPublishingQuery:
    """Inputs for one channel-analytics read.

    ``weeks`` bounds the velocity window; the read also always covers the
    last 30 days so the per-month totals stay correct for small windows.
    ``now`` is injectable for tests; ``None`` reads the wall clock.
    """

    db: AsyncSession
    author_id: str | None = None
    weeks: int = 8
    now: datetime | None = None


@dataclass(frozen=True)
class ChannelAnalytics:
    """Per-channel published counts + weekly velocity from one event read."""

    channels: list[ChannelPublishing]
    velocity: list[AnalyticsVelocityWeek]


class PublishingCounter(Protocol):
    """Publishes events and totals of one channel."""

    async def published_since(
        self, db: AsyncSession, author_id: str | None, since: datetime
    ) -> list[datetime]:
        """The publish timestamps at or after ``since``, any order."""
        ...

    async def published_total(self, db: AsyncSession, author_id: str | None) -> int:
        """How many pieces of content the channel has published, all time."""
        ...


class BlogPublishingCounter:
    """Blog-post publishes, scoped to the author when given."""

    @staticmethod
    async def published_since(
        db: AsyncSession, author_id: str | None, since: datetime
    ) -> list[datetime]:
        """The ``published_at`` of blog posts published at or after ``since``."""
        query = select(BlogPostModel.published_at).where(
            BlogPostModel.published_at.is_not(None),
            BlogPostModel.published_at >= since,
        )
        if author_id:
            query = query.where(BlogPostModel.author_id == author_id)
        rows = await db.scalars(query)
        return [_as_aware(at) for at in rows.all() if at is not None]

    @staticmethod
    async def published_total(db: AsyncSession, author_id: str | None) -> int:
        """Every published blog post, scoped to the author when given."""
        query = (
            select(func.count())
            .select_from(BlogPostModel)
            .where(BlogPostModel.published_at.is_not(None))
        )
        if author_id:
            query = query.where(BlogPostModel.author_id == author_id)
        return await _count(db, query)


class CarouselPublishingCounter:
    """Carousel publishes to Instagram, from the two publish ledgers.

    A carousel counts once no matter whether the autopilot or the manual
    route published it; the newest publish timestamp wins. Scoped to the
    carousel owner when an author is given.
    """

    @staticmethod
    async def published_since(
        db: AsyncSession, author_id: str | None, since: datetime
    ) -> list[datetime]:
        """One timestamp per carousel published at or after ``since``."""
        published = CarouselPublishingCounter._published_union(since).subquery()
        query = (
            select(func.max(published.c.published_at))
            .select_from(
                published.join(
                    _CAROUSELS, _CAROUSELS.c.id == published.c.carousel_project_id
                )
            )
            .group_by(published.c.carousel_project_id)
        )
        if author_id:
            query = query.where(_CAROUSELS.c.owner_id == author_id)
        rows = await db.scalars(query)
        return [_as_aware(at) for at in rows.all()]

    @staticmethod
    async def published_total(db: AsyncSession, author_id: str | None) -> int:
        """Distinct carousels with an Instagram publish record."""
        published = CarouselPublishingCounter._published_union(None).subquery()
        query = select(
            func.count(func.distinct(published.c.carousel_project_id))
        ).select_from(
            published.join(
                _CAROUSELS, _CAROUSELS.c.id == published.c.carousel_project_id
            )
        )
        if author_id:
            query = query.where(_CAROUSELS.c.owner_id == author_id)
        return await _count(db, query)

    @staticmethod
    def _published_union(
        since: datetime | None,
    ) -> CompoundSelect[tuple[object, object]]:
        """Autopilot runs and manual publishes that carry an Instagram media id."""
        run_events = select(
            _RUNS.c.carousel_project_id,
            _RUNS.c.updated_at.label("published_at"),
        ).where(_RUNS.c.ig_post_id.is_not(None))
        manual_events = select(
            _MANUAL.c.carousel_project_id,
            _MANUAL.c.claimed_at.label("published_at"),
        ).where(_MANUAL.c.ig_post_id.is_not(None))
        if since is not None:
            run_events = run_events.where(_RUNS.c.updated_at >= since)
            manual_events = manual_events.where(_MANUAL.c.claimed_at >= since)
        return union_all(run_events, manual_events)


CHANNEL_COUNTERS: dict[str, PublishingCounter] = {
    CHANNEL_BLOG: BlogPublishingCounter(),
    CHANNEL_CAROUSEL: CarouselPublishingCounter(),
}


async def channel_publishing(query: ChannelPublishingQuery) -> ChannelAnalytics:
    """Per-channel counts and weekly velocity from one event read per channel."""
    now = query.now or datetime.now(UTC)
    window = timedelta(days=max(query.weeks * 7, 30))
    events: dict[str, list[datetime]] = {}
    totals: dict[str, int] = {}
    for channel, counter in CHANNEL_COUNTERS.items():
        events[channel] = await counter.published_since(
            query.db, query.author_id, now - window
        )
        totals[channel] = await counter.published_total(query.db, query.author_id)
    return ChannelAnalytics(
        channels=_counts(events, totals, now),
        velocity=_buckets(events, now, query.weeks),
    )


def _counts(
    events: dict[str, list[datetime]], totals: dict[str, int], now: datetime
) -> list[ChannelPublishing]:
    """Per-channel totals from the events of the shared window."""
    return [
        ChannelPublishing(
            channel=channel,
            published_total=totals[channel],
            published_this_week=_since(published, now - _WEEK),
            published_this_month=_since(published, now - _MONTH),
        )
        for channel, published in events.items()
    ]


def _buckets(
    events: dict[str, list[datetime]], now: datetime, weeks: int
) -> list[AnalyticsVelocityWeek]:
    """One velocity bucket per week, oldest first."""
    return [_bucket(events, now, week_idx) for week_idx in range(weeks - 1, -1, -1)]


def _bucket(
    events: dict[str, list[datetime]], now: datetime, week_idx: int
) -> AnalyticsVelocityWeek:
    """One week bucket: the per-channel counts and their sum."""
    start = now - timedelta(days=(week_idx + 1) * 7)
    end = now - timedelta(days=week_idx * 7)
    channels = {
        channel: sum(1 for at in published if start <= at < end)
        for channel, published in events.items()
    }
    return AnalyticsVelocityWeek(
        week_start=start.date().isoformat(),
        published_count=sum(channels.values()),
        channels=channels,
    )


def _since(events: list[datetime], cutoff: datetime) -> int:
    """How many publish events happened at or after the cutoff."""
    return sum(1 for at in events if at >= cutoff)


def _as_aware(value: datetime) -> datetime:
    """Normalize a stored datetime to tz-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def _count(db: AsyncSession, query: Select[tuple[int]]) -> int:
    """The scalar count of a query, 0 when the database returns nothing."""
    total = await db.scalar(query)
    return total if isinstance(total, int) else 0


__all__ = [
    "CHANNEL_COUNTERS",
    "BlogPublishingCounter",
    "CarouselPublishingCounter",
    "ChannelAnalytics",
    "ChannelPublishingQuery",
    "PublishingCounter",
    "channel_publishing",
]
