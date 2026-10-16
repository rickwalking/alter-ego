"""Content-mode columns of ``carousel_projects`` (AE-0373, ADR-0021).

A mixin plus the entity mapping, kept out of ``carousel.py`` (already over the
400-line limit). Every column is nullable: NULL ``content_mode`` is Radar IA.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_MAX_CHARS,
    CTA_GOAL_MAX_CHARS,
    HOOK_TEXT_COLUMN_CHARS,
    POV_FORMAT_MAX_CHARS,
    POV_PERSONAL_PROOF_MAX_CHARS,
    POV_THESIS_MAX_CHARS,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.news_quote import (
    NewsQuote,
    quote_rows,
    quotes_from_rows,
)

FK_HOOK_ASSET = "fk_carousel_projects_hook_asset"
_ASSET_FK = "carousel_creator_assets.id"
_FK_SET_NULL = "SET NULL"
_UUID_CHARS = 36


class ContentModeFields(TypedDict):
    """The entity keyword arguments the content-mode columns hydrate."""

    content_mode: str | None
    pov_thesis: str | None
    pov_personal_proof: str | None
    pov_format: str | None
    slide_count: int | None
    cta_goal: str | None
    hook_text: str | None
    hook_asset_id: UUID | None
    pov_quotes: tuple[NewsQuote, ...]
    pov_sources: tuple[str, ...]


class CarouselContentModeColumns:
    """Columns mixed into ``CarouselProjectModel``."""

    content_mode: Mapped[str | None] = mapped_column(
        String(CONTENT_MODE_MAX_CHARS), nullable=True
    )
    pov_thesis: Mapped[str | None] = mapped_column(
        String(POV_THESIS_MAX_CHARS), nullable=True
    )
    pov_personal_proof: Mapped[str | None] = mapped_column(
        String(POV_PERSONAL_PROOF_MAX_CHARS), nullable=True
    )
    pov_format: Mapped[str | None] = mapped_column(
        String(POV_FORMAT_MAX_CHARS), nullable=True
    )
    slide_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cta_goal: Mapped[str | None] = mapped_column(
        String(CTA_GOAL_MAX_CHARS), nullable=True
    )
    hook_text: Mapped[str | None] = mapped_column(
        String(HOOK_TEXT_COLUMN_CHARS), nullable=True
    )
    hook_asset_id: Mapped[str | None] = mapped_column(
        String(_UUID_CHARS),
        ForeignKey(_ASSET_FK, name=FK_HOOK_ASSET, ondelete=_FK_SET_NULL),
        nullable=True,
    )
    # AE-0406 (ADR-0023): ``pov_news`` quotes and the topic sources (NULL = none).
    pov_quotes: Mapped[list[dict[str, str]] | None] = mapped_column(JSON, nullable=True)
    pov_sources: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    def content_mode_fields(self) -> ContentModeFields:
        """The entity keyword arguments for these columns."""
        return ContentModeFields(
            content_mode=self.content_mode,
            pov_thesis=self.pov_thesis,
            pov_personal_proof=self.pov_personal_proof,
            pov_format=self.pov_format,
            slide_count=self.slide_count,
            cta_goal=self.cta_goal,
            hook_text=self.hook_text,
            hook_asset_id=UUID(self.hook_asset_id) if self.hook_asset_id else None,
            pov_quotes=quotes_from_rows(self.pov_quotes),
            pov_sources=_source_list(self.pov_sources),
        )

    def write_content_mode(self, entity: CarouselProject) -> None:
        """Copy every content-mode field from a new entity (create)."""
        self.content_mode = entity.content_mode
        self.pov_thesis = entity.pov_thesis
        self.pov_personal_proof = entity.pov_personal_proof
        self.pov_format = entity.pov_format
        self.slide_count = entity.slide_count
        self.cta_goal = entity.cta_goal
        self.pov_quotes = quote_rows(entity.pov_quotes) or None
        self.pov_sources = list(entity.pov_sources) or None
        self.write_owner_edits(entity)

    def write_owner_edits(self, entity: CarouselProject) -> None:
        """Copy only the owner-editable fields (update): hook text and photo."""
        self.hook_text = entity.hook_text
        self.hook_asset_id = str(entity.hook_asset_id) if entity.hook_asset_id else None


def _source_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(item for item in raw if isinstance(item, str))


__all__ = ["CarouselContentModeColumns", "ContentModeFields"]
