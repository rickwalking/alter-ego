"""SQLAlchemy model of the autopilot's record of one cover generation.

One row per generation the autopilot started for a fresh carousel: it marks
the generation as the autopilot's and keeps slide 1's cover fields when it was
scheduled (the owner-choice baseline). The drive's gates read it from the
database, so a restart between the cover succeeding and the next gate never
loses the cover or the owner's choice. Plain asset ids, no foreign key: a
deleted asset must not erase the record. Deleting the generation removes it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from rag_backend.domain.constants.cover_generation import (
    TABLE_COVER_AUTOPILOT_BASELINES,
    TABLE_COVER_GENERATIONS,
)
from rag_backend.infrastructure.database.config import Base

_ID_LENGTH = 36


class CarouselCoverAutopilotBaselineModel(Base):
    """The autopilot's generation and slide 1's cover fields at scheduling."""

    __tablename__ = TABLE_COVER_AUTOPILOT_BASELINES

    generation_id: Mapped[str] = mapped_column(
        String(_ID_LENGTH),
        ForeignKey(f"{TABLE_COVER_GENERATIONS}.id", ondelete="CASCADE"),
        primary_key=True,
    )
    slide_cover_asset_id: Mapped[str | None] = mapped_column(
        String(_ID_LENGTH), nullable=True
    )
    hook_asset_id: Mapped[str | None] = mapped_column(String(_ID_LENGTH), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
