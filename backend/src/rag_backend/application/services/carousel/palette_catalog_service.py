"""Application service for custom-palette CRUD (AE-0270).

Orchestrates create/update/archive over the ``PaletteRepository`` **port** only —
no infrastructure import, so the application→infrastructure ratchet is untouched
(the API layer constructs the concrete adapter). Pure request-shape validation
(hex/name/keywords) already happened in the Pydantic schema; this layer owns the
DB-dependent rules: server-generated immutable slugs (D8), cross-catalog keyword
de-duplication so AUTO detection stays deterministic (skeptical G5), and the
not-found / archived-is-terminal (G8) decisions. Name + slug uniqueness is left to
the DB unique indexes; the resulting ``IntegrityError`` is mapped to 409 by the
route (skeptical F3 — an app-level pre-check would race).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from rag_backend.domain.constants.carousel_themes import (
    BRAND_PALETTES,
    CAROUSEL_THEMES,
)
from rag_backend.domain.constants.palette_catalog import (
    RESERVED_SLUGS,
    SLUG_CHAR_RE,
    SLUG_ID_SUFFIX_LEN,
    SLUG_MAX_LEN,
)
from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.domain.protocols.palette import PaletteRepository

_SLUG_FALLBACK = "palette"
_SLUG_BASE_MAX = SLUG_MAX_LEN - SLUG_ID_SUFFIX_LEN - 1  # room for "-<suffix>"


class PaletteNotFoundError(Exception):
    """Raised when a custom-palette id is unknown or archived (terminal, G8)."""


@dataclass(frozen=True)
class PaletteCreateCommand:
    """Validated inputs for creating a custom palette."""

    name: str
    primary: str
    accent: str
    background: str
    mode: PaletteMode
    keywords: tuple[str, ...]
    created_by: str | None


@dataclass(frozen=True)
class PaletteUpdateCommand:
    """Validated partial inputs for editing a custom palette (``None`` = keep)."""

    name: str | None = None
    primary: str | None = None
    accent: str | None = None
    background: str | None = None
    mode: PaletteMode | None = None
    keywords: tuple[str, ...] | None = None


def is_root_key(ref: str) -> bool:
    """True if ``ref`` names a read-only root palette (registry or brand key)."""
    return ref in CAROUSEL_THEMES or ref in BRAND_PALETTES


def make_slug(name: str, palette_id: UUID) -> str:
    """Build an immutable, URL-safe, globally-unique slug from the name + id (D8).

    The id suffix guarantees global uniqueness (so an archived palette never
    blocks recreating its name, G8) and means the slug can never exactly equal a
    reserved sub-route. Non-``[a-z0-9]`` runs collapse to single hyphens.
    """
    base = SLUG_CHAR_RE.sub("-", name.lower()).strip("-")
    if not base or base in RESERVED_SLUGS:
        base = _SLUG_FALLBACK
    return f"{base[:_SLUG_BASE_MAX]}-{palette_id.hex[:SLUG_ID_SUFFIX_LEN]}"


def _build_new_palette(command: PaletteCreateCommand) -> CustomPalette:
    palette_id = uuid4()
    return CustomPalette(
        id=palette_id,
        name=command.name,
        slug=make_slug(command.name, palette_id),
        palette=Palette(command.primary, command.accent, command.background),
        mode=command.mode,
        keywords=command.keywords,
        created_by=command.created_by,
    )


def _apply_update(
    existing: CustomPalette, command: PaletteUpdateCommand
) -> CustomPalette:
    merged_colours = Palette(
        primary=command.primary or existing.palette.primary,
        accent=command.accent or existing.palette.accent,
        background=command.background or existing.palette.background,
    )
    keywords = existing.keywords if command.keywords is None else command.keywords
    return replace(
        existing,
        name=command.name or existing.name,
        palette=merged_colours,
        mode=command.mode or existing.mode,
        keywords=keywords,
    )


class PaletteCatalogService:
    """CRUD over the global custom-palette catalog (port-only)."""

    def __init__(self, repo: PaletteRepository) -> None:
        self._repo = repo

    async def list_active(self) -> list[CustomPalette]:
        """Return all non-archived custom palettes (catalog source)."""
        return await self._repo.list_active()

    async def create(self, command: PaletteCreateCommand) -> CustomPalette:
        """Create a custom palette (slug generated; keywords cross-deduped)."""
        palette = _build_new_palette(command)
        deduped = await self._dedupe_keywords(palette.keywords, exclude_id=None)
        return await self._repo.add(replace(palette, keywords=deduped))

    async def update(
        self, palette_id: UUID, command: PaletteUpdateCommand
    ) -> CustomPalette:
        """Edit an active custom palette. Archived/unknown → ``PaletteNotFoundError``."""
        existing = await self._repo.get_by_id(palette_id)
        if existing is None or existing.archived:
            raise PaletteNotFoundError(str(palette_id))
        merged = _apply_update(existing, command)
        deduped = await self._dedupe_keywords(merged.keywords, exclude_id=palette_id)
        return await self._repo.update(replace(merged, keywords=deduped))

    async def archive(self, palette_id: UUID) -> bool:
        """Soft-delete a custom palette. False if the id is unknown."""
        return await self._repo.archive(palette_id)

    async def _dedupe_keywords(
        self, keywords: tuple[str, ...], exclude_id: UUID | None
    ) -> tuple[str, ...]:
        if not keywords:
            return keywords
        actives = await self._repo.list_active()
        claimed = {
            keyword
            for palette in actives
            if palette.id != exclude_id
            for keyword in palette.keywords
        }
        return tuple(keyword for keyword in keywords if keyword not in claimed)


__all__ = [
    "PaletteCatalogService",
    "PaletteCreateCommand",
    "PaletteNotFoundError",
    "PaletteUpdateCommand",
    "is_root_key",
    "make_slug",
]
