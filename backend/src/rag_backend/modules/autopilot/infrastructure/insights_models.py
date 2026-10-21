"""ORM row for ``instagram_post_insights`` (ADR-0021 D11).

One row per Instagram media id: the latest snapshot. Every metric column is
nullable because the Graph API may omit a metric; ``NULL`` is "n/d".
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.modules.autopilot.constants import IG_IDENTIFIER_LENGTH
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


__all__ = ["InstagramAudienceHoursModel", "InstagramPostInsightsModel"]
