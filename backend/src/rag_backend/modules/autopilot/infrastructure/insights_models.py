"""ORM row for ``instagram_post_insights`` (ADR-0021 D11).

One row per Instagram media id: the latest snapshot. Every metric column is
nullable because the Graph API may omit a metric; ``NULL`` is "n/d".
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.modules.autopilot.constants import IG_IDENTIFIER_LENGTH
from rag_backend.modules.autopilot.ig_media_constants import (
    CAPTION_EXCERPT_LENGTH,
    INDEX_IG_MEDIA_POSTED_AT,
    MEDIA_TYPE_LENGTH,
    PRODUCT_TYPE_LENGTH,
    TABLE_IG_MEDIA,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotOrmBase
from rag_backend.modules.autopilot.insights_constants import TABLE_POST_INSIGHTS
from rag_backend.modules.autopilot.recommend_constants import TABLE_AUDIENCE_HOURS


class InstagramPostInsightsModel(AutopilotOrmBase):
    """The last insights snapshot read for one published post."""

    __tablename__ = TABLE_POST_INSIGHTS

    media_id: Mapped[str] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), primary_key=True
    )
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    follows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_visits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_interactions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_watch_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_watch_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class InstagramAudienceHoursModel(AutopilotOrmBase):
    """The cached ``online_followers`` of one account.

    ``online_followers`` maps the UTC hour (``"0"``-``"23"``) to followers
    online. ``checked_at`` is the last Graph attempt; ``fetched_at`` the last
    success (None until one succeeds).
    """

    __tablename__ = TABLE_AUDIENCE_HOURS

    ig_user_id: Mapped[str] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), primary_key=True
    )
    online_followers: Mapped[dict[str, int]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class IgMediaModel(AutopilotOrmBase):
    """One Instagram media object seen on the account, caption clipped to 280."""

    __tablename__ = TABLE_IG_MEDIA
    __table_args__ = (Index(INDEX_IG_MEDIA_POSTED_AT, "posted_at"),)

    media_id: Mapped[str] = mapped_column(
        String(IG_IDENTIFIER_LENGTH), primary_key=True
    )
    media_type: Mapped[str] = mapped_column(String(MEDIA_TYPE_LENGTH), nullable=False)
    media_product_type: Mapped[str | None] = mapped_column(
        String(PRODUCT_TYPE_LENGTH), nullable=True
    )
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_excerpt: Mapped[str | None] = mapped_column(
        String(CAPTION_EXCERPT_LENGTH), nullable=True
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = [
    "IgMediaModel",
    "InstagramAudienceHoursModel",
    "InstagramPostInsightsModel",
]
