"""SQLAlchemy ``ScheduleSignalsSource``.

- **audience**: the account's ``online_followers``, cached in
  ``instagram_audience_hours`` and read from Graph at most once a day. A Graph
  failure is logged and the cached hours (or none) are used; the attempt is
  still recorded, so a failing metric is not retried on every tap.
- **posts**: our published posts joined to their stored insights
  (``instagram_post_insights``). The publish time is the run's
  ``scheduled_at`` when it kept one, else its last update; a manual publish
  uses its claim time.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.recommend import (
    PostEngagement,
    ScheduleSignals,
    engagement_rate,
)
from rag_backend.modules.autopilot.domain.schedule_ports import AudienceGateway
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramAudienceHoursModel,
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware
from rag_backend.modules.autopilot.recommend_constants import (
    AUDIENCE_TTL_HOURS,
    LOG_AUDIENCE_FETCH_FAILED,
    LOG_AUDIENCE_SAVE_FAILED,
    PERFORMANCE_POST_LIMIT,
)

logger = structlog.get_logger()

_INSIGHTS = InstagramPostInsightsModel
_METRIC_COLUMNS = (_INSIGHTS.reach, _INSIGHTS.saved, _INSIGHTS.shares)


@dataclass(frozen=True, kw_only=True)
class ScheduleSignalsConfig:
    """The request session, the clock, and the account's Graph reader."""

    session: AsyncSession
    clock: Clock
    audience: AudienceGateway | None
    ig_user_id: str


@dataclass(frozen=True, kw_only=True)
class _Fetch:
    row: InstagramAudienceHoursModel | None
    hours: dict[int, int] | None


class SqlScheduleSignals:
    """Reads the recommender's signals for one webhook request."""

    def __init__(self, config: ScheduleSignalsConfig) -> None:
        self._config = config

    async def load(self) -> ScheduleSignals:
        """Audience hours and post engagement; Graph failures fall back."""
        return ScheduleSignals(
            audience=await self._audience(), posts=tuple(await self._posts())
        )

    async def _audience(self) -> dict[int, int]:
        user_id = self._config.ig_user_id.strip()
        if not user_id:
            return {}
        row = await self._config.session.get(InstagramAudienceHoursModel, user_id)
        if row is not None and not self._due(row):
            return _hours(row)
        gateway = self._config.audience
        if gateway is None:
            return _hours(row) if row is not None else {}
        hours = await _fetch(gateway)
        await self._save(_Fetch(row=row, hours=hours))
        if hours is not None:
            return hours
        return _hours(row) if row is not None else {}

    def _due(self, row: InstagramAudienceHoursModel) -> bool:
        checked = aware(row.checked_at)
        ttl = timedelta(hours=AUDIENCE_TTL_HOURS)
        return checked is None or self._config.clock.now() - checked >= ttl

    async def _save(self, fetch: _Fetch) -> None:
        """Record the attempt (and the hours on success) in a savepoint.

        When a concurrent request saved first, its hours serve this one later.
        """
        now = self._config.clock.now()
        session = self._config.session
        try:
            async with session.begin_nested():
                row = fetch.row or _new_row(self._config.ig_user_id.strip(), now)
                row.checked_at = now
                if fetch.hours is not None:
                    row.online_followers = {str(h): c for h, c in fetch.hours.items()}
                    row.fetched_at = now
                session.add(row)
        except SQLAlchemyError as exc:
            logger.warning(LOG_AUDIENCE_SAVE_FAILED, error=type(exc).__name__)

    async def _posts(self) -> list[PostEngagement]:
        found = [*await self._run_posts(), *await self._manual_posts()]
        return [post for post in found if post is not None]

    async def _run_posts(self) -> list[PostEngagement | None]:
        run = AutopilotRunModel
        published = func.coalesce(run.scheduled_at, run.updated_at)
        result = await self._config.session.execute(
            select(published, *_METRIC_COLUMNS, _INSIGHTS.total_interactions)
            .join(_INSIGHTS, _INSIGHTS.media_id == run.ig_post_id)
            .order_by(published.desc())
            .limit(PERFORMANCE_POST_LIMIT)
        )
        return [_engagement(row) for row in result.all()]

    async def _manual_posts(self) -> list[PostEngagement | None]:
        manual = ManualPublishModel
        result = await self._config.session.execute(
            select(manual.claimed_at, *_METRIC_COLUMNS, _INSIGHTS.total_interactions)
            .join(_INSIGHTS, _INSIGHTS.media_id == manual.ig_post_id)
            .order_by(manual.claimed_at.desc())
            .limit(PERFORMANCE_POST_LIMIT)
        )
        return [_engagement(row) for row in result.all()]


async def _fetch(gateway: AudienceGateway) -> dict[int, int] | None:
    """The Graph hours, or None after logging any failure (silent fallback)."""
    try:
        return await gateway.online_followers()
    except Exception as exc:
        logger.warning(LOG_AUDIENCE_FETCH_FAILED, error=type(exc).__name__)
        return None


def _new_row(user_id: str, now: datetime) -> InstagramAudienceHoursModel:
    return InstagramAudienceHoursModel(
        ig_user_id=user_id, online_followers={}, checked_at=now, fetched_at=None
    )


def _hours(row: InstagramAudienceHoursModel) -> dict[int, int]:
    stored = row.online_followers or {}
    return {int(hour): int(count) for hour, count in stored.items() if hour.isdigit()}


def _engagement(row: Sequence[object]) -> PostEngagement | None:
    at, reach, saved, shares, interactions = row
    published = aware(at) if isinstance(at, datetime) else None
    metrics = InsightMetrics(
        reach=_count(reach),
        saved=_count(saved),
        shares=_count(shares),
        total_interactions=_count(interactions),
    )
    rate = engagement_rate(metrics)
    if published is None or rate is None:
        return None
    return PostEngagement(published_at=published, rate=rate)


def _count(value: object) -> int | None:
    return value if isinstance(value, int) else None


__all__ = ["ScheduleSignalsConfig", "SqlScheduleSignals"]
