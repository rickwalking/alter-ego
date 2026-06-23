"""Port for custom-palette persistence (AE-0269).

The domain defines this Protocol; the infrastructure layer implements it against
PostgreSQL. The resolver (read paths) and the AE-0270 CRUD API (write paths)
depend on this port, never on the concrete adapter.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from rag_backend.domain.models.palette import CustomPalette


class PaletteRepository(Protocol):
    """Async persistence port for the global custom-palette catalog."""

    async def get_by_id(self, palette_id: UUID) -> CustomPalette | None:
        """Return the palette (active OR archived), or None if absent.

        Archived palettes resolve so existing carousels keep working; the
        carousel itself renders from its snapshot, so this lookup is only for
        explicit re-resolution paths.
        """
        ...

    async def list_active(self) -> list[CustomPalette]:
        """Return all non-archived palettes (catalog + AUTO keyword pool)."""
        ...

    async def add(self, palette: CustomPalette) -> CustomPalette:
        """Persist a new palette. Raises on name/slug uniqueness conflict."""
        ...

    async def update(self, palette: CustomPalette) -> CustomPalette:
        """Persist edits to an existing palette (slug is immutable, D8)."""
        ...

    async def archive(self, palette_id: UUID) -> bool:
        """Soft-delete: set ``archived``. Returns False if the id is unknown."""
        ...
