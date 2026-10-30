"""SQL cache of Instagram media the account has posted.

Project links come from autopilot runs and the manual publish ledger. The
carousel topic is read through a table clause, not the carousel ORM.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import column, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.ig_media import (
    BaselineSample,
    IgMedia,
    MediaProject,
    TimeWindow,
)
from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.ig_media_constants import (
    BASELINE_ROW_CAP,
    IG_MEDIA_LIST_TTL_MINUTES,
    IG_MEDIA_QUERY_CAP,
    PRODUCT_FEED,
    PRODUCT_REELS,
)
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    IgMediaModel,
    InstagramPostInsightsModel,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware

_CAROUSELS = table("carousel_projects", column("id"), column("topic"))
_PRODUCTS = (PRODUCT_FEED, PRODUCT_REELS)


class SqlIgMediaStore:
    """``IgMediaStore`` on one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_is_fresh(self, now: datetime) -> bool:
        """True when the newest listing is inside the TTL."""
        newest = await self._session.scalar(
            select(IgMediaModel.listed_at).order_by(IgMediaModel.listed_at.desc()).limit(1)
        )
        if not isinstance(newest, datetime):
            return False
        fresh_at = aware(newest)
        if fresh_at is None:
            return False
        return now - fresh_at < timedelta(minutes=IG_MEDIA_LIST_TTL_MINUTES)

    async def upsert(self, items: Sequence[IgMedia], listed_at: datetime) -> None:
        """Insert or replace each walked media row."""
        for item in items:
            await self._upsert_one(item, listed_at)
        await self._session.flush()

    async def in_window(self, window: TimeWindow) -> list[IgMedia]:
        """Newest posts inside the window."""
        rows = await self._session.scalars(
            select(IgMediaModel)
            .where(
                IgMediaModel.posted_at >= window.start,
                IgMediaModel.posted_at < window.end,
            )
            .order_by(IgMediaModel.posted_at.desc())
            .limit(IG_MEDIA_QUERY_CAP)
        )
        return [_media(row) for row in rows]

    async def projects(self, media_ids: Sequence[str]) -> dict[str, MediaProject]:
        """The first carousel link found for each media id."""
        if not media_ids:
            return {}
        found: dict[str, MediaProject] = {}
        for row in await self._project_rows(AutopilotRunModel, media_ids):
            found.setdefault(row[0], _project(row))
        for row in await self._manual_rows(media_ids):
            found.setdefault(row[0], _project(row))
        return found

    async def baseline_samples(self, window: TimeWindow) -> list[BaselineSample]:
        """Up to the cap of settled posts for each product type."""
        samples: list[BaselineSample] = []
        for product in _PRODUCTS:
            samples.extend(await self._samples(product, window))
        return samples

    async def commit(self) -> None:
        """Commit the session."""
        await self._session.commit()

    async def _upsert_one(self, item: IgMedia, listed_at: datetime) -> None:
        row = await self._session.get(IgMediaModel, item.media_id)
        if row is None:
            row = IgMediaModel(
                media_id=item.media_id,
                media_type=item.media_type,
                posted_at=item.posted_at,
                listed_at=listed_at,
            )
            self._session.add(row)
        _fill(row, item, listed_at)

    async def _samples(self, product: str, window: TimeWindow) -> list[BaselineSample]:
        result = await self._session.execute(
            select(IgMediaModel, InstagramPostInsightsModel)
            .outerjoin(
                InstagramPostInsightsModel,
                InstagramPostInsightsModel.media_id == IgMediaModel.media_id,
            )
            .where(
                IgMediaModel.media_product_type == product,
                IgMediaModel.posted_at >= window.start,
                IgMediaModel.posted_at <= window.end,
            )
            .order_by(IgMediaModel.posted_at.desc())
            .limit(BASELINE_ROW_CAP)
        )
        return [_sample(product, insight) for _media_row, insight in result.all()]

    async def _project_rows(
        self, model: type[AutopilotRunModel], media_ids: Sequence[str]
    ) -> list[tuple[str, object, object]]:
        result = await self._session.execute(
            select(model.ig_post_id, model.carousel_project_id, _CAROUSELS.c.topic)
            .outerjoin(_CAROUSELS, _CAROUSELS.c.id == model.carousel_project_id)
            .where(model.ig_post_id.in_(list(media_ids)))
        )
        return [_triple(row) for row in result.all()]

    async def _manual_rows(
        self, media_ids: Sequence[str]
    ) -> list[tuple[str, object, object]]:
        manual = ManualPublishModel
        result = await self._session.execute(
            select(manual.ig_post_id, manual.carousel_project_id, _CAROUSELS.c.topic)
            .outerjoin(_CAROUSELS, _CAROUSELS.c.id == manual.carousel_project_id)
            .where(manual.ig_post_id.in_(list(media_ids)))
        )
        return [_triple(row) for row in result.all()]


def _fill(row: IgMediaModel, item: IgMedia, listed_at: datetime) -> None:
    row.media_type = item.media_type
    row.media_product_type = item.media_product_type
    row.permalink = item.permalink
    row.caption_excerpt = item.caption_excerpt
    row.posted_at = item.posted_at
    row.like_count = item.like_count
    row.comments_count = item.comments_count
    row.listed_at = listed_at


def _media(row: IgMediaModel) -> IgMedia:
    posted = aware(row.posted_at)
    return IgMedia(
        media_id=row.media_id,
        media_type=row.media_type,
        media_product_type=row.media_product_type,
        permalink=row.permalink,
        caption_excerpt=row.caption_excerpt,
        posted_at=posted if posted is not None else row.posted_at,
        like_count=row.like_count,
        comments_count=row.comments_count,
    )


def _sample(product: str, row: InstagramPostInsightsModel | None) -> BaselineSample:
    metrics = InsightMetrics() if row is None else _metrics(row)
    return BaselineSample(product_type=product, metrics=metrics)


def _metrics(row: InstagramPostInsightsModel) -> InsightMetrics:
    return InsightMetrics(
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
    )


def _project(row: tuple[str, object, object]) -> MediaProject:
    _media_id, project_id, topic = row
    return MediaProject(
        carousel_project_id=str(project_id) if project_id else None,
        topic=topic if isinstance(topic, str) else None,
    )


def _triple(row: Sequence[object]) -> tuple[str, object, object]:
    media_id, project_id, topic = row
    return str(media_id), project_id, topic


__all__ = ["SqlIgMediaStore"]
