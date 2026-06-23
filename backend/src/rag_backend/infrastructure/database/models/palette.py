"""SQLAlchemy model for the global custom-palette catalog (AE-0269).

Maps the ``palettes`` table to/from the ``CustomPalette`` domain entity. Two
DB-level constraints enforce uniqueness under concurrency (skeptical F3/G3):
a partial unique index on ``name`` for active rows, and a plain unique index on
``slug`` across all rows.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.infrastructure.database.config import Base

_HEX_LEN = 7
_NAME_MAX = 80
_SLUG_MAX = 80
_MODE_MAX = 8


class PaletteModel(Base):
    """ORM row for one custom palette."""

    __tablename__ = "palettes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(_NAME_MAX), nullable=False)
    slug: Mapped[str] = mapped_column(String(_SLUG_MAX), nullable=False)
    primary: Mapped[str] = mapped_column(String(_HEX_LEN), nullable=False)
    accent: Mapped[str] = mapped_column(String(_HEX_LEN), nullable=False)
    background: Mapped[str] = mapped_column(String(_HEX_LEN), nullable=False)
    mode: Mapped[str] = mapped_column(String(_MODE_MAX), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Active palette names are unique; archived rows are excluded so a
        # name can be reused after its palette is archived (partial index is a
        # PostgreSQL feature — ignored by other dialects in unit tests).
        Index(
            "uq_palettes_name_active",
            "name",
            unique=True,
            postgresql_where=text("archived = false"),
        ),
        # Slugs are globally unique (incl. archived) so they never collide or
        # get silently reused (D8/F1).
        Index("uq_palettes_slug", "slug", unique=True),
    )

    def to_domain(self) -> CustomPalette:
        """Build the ``CustomPalette`` entity from this row."""
        return CustomPalette(
            id=self.id,
            name=self.name,
            slug=self.slug,
            palette=Palette(self.primary, self.accent, self.background),
            mode=PaletteMode(self.mode),
            keywords=tuple(self.keywords),
            archived=self.archived,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: CustomPalette) -> PaletteModel:
        """Build an ORM row from the ``CustomPalette`` entity."""
        return cls(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            primary=entity.palette.primary,
            accent=entity.palette.accent,
            background=entity.palette.background,
            mode=entity.mode.value,
            keywords=list(entity.keywords),
            archived=entity.archived,
            created_by=entity.created_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
