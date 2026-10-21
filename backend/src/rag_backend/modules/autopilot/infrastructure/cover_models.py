"""ORM row for ``autopilot_cover_assets`` (ADR-0024).

One row per GrokBot cover upload. ``id`` is the ``asset_id`` the scout gets;
the image itself is a ``carousel_creator_assets`` row with role ``cover``.
``topic_candidate_id`` is set when a stored topic uses the cover (one use);
unused rows older than 6 hours are swept.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.domain.constants.slide_cover import COVER_KIND_MAX_CHARS
from rag_backend.modules.autopilot.constants import ON_DELETE_SET_NULL
from rag_backend.modules.autopilot.cover_constants import (
    COVER_SOURCE_URL_MAX_CHARS,
    COVER_TOPIC_FK,
    COVER_UUID_CHARS,
    CREATOR_ASSET_FK,
    FK_COVER_CREATOR_ASSET,
    FK_COVER_TOPIC,
    INDEX_COVER_CREATED_AT,
    TABLE_COVER_ASSETS,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotOrmBase
from rag_backend.modules.autopilot.recovery_constants import ON_DELETE_CASCADE


class AutopilotCoverAssetModel(AutopilotOrmBase):
    """A GrokBot cover: its creator asset, kind, source and first topic."""

    __tablename__ = TABLE_COVER_ASSETS

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    creator_asset_id: Mapped[str] = mapped_column(
        String(COVER_UUID_CHARS),
        ForeignKey(
            CREATOR_ASSET_FK, name=FK_COVER_CREATOR_ASSET, ondelete=ON_DELETE_CASCADE
        ),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(COVER_KIND_MAX_CHARS), nullable=False)
    source_url: Mapped[str | None] = mapped_column(
        String(COVER_SOURCE_URL_MAX_CHARS), nullable=True
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(COVER_TOPIC_FK, name=FK_COVER_TOPIC, ondelete=ON_DELETE_SET_NULL),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index(INDEX_COVER_CREATED_AT, "created_at"),)


__all__ = ["AutopilotCoverAssetModel"]
