"""Custom palette entity (AE-0269).

A user-created palette in the global catalog. The curated *root* palettes stay
in the typed ``PALETTE_REGISTRY`` (read-only); custom palettes are mutable rows
persisted by a ``PaletteRepository``. The colour triple and light/dark mode
reuse the AE-0266 value objects so a custom palette speaks the same vocabulary
as a root one. Image style is NOT stored — it is derived from ``mode`` at
resolve time (a light palette can therefore never be paired with a dark image
strategy, ADR-0019 D3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from rag_backend.domain.constants.palette_types import Palette, PaletteMode


@dataclass
class CustomPalette:
    """A user-created, globally-shared palette (AE-0269)."""

    name: str
    slug: str
    palette: Palette
    mode: PaletteMode
    id: UUID = field(default_factory=uuid4)
    keywords: tuple[str, ...] = ()
    archived: bool = False
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def reference(self) -> str:
        """The stable string stored in ``CarouselProject.theme`` (the UUID, D6).

        Never the slug — the slug is display-only and must not be the foreign
        key, so a renamed/recreated slug can never silently re-point a project
        (skeptical F1).
        """
        return str(self.id)
