"""Unit tests for the palette catalog service (AE-0270).

Feature: Custom palette CRUD API (tests/features/palette_crud_api.feature)
Exercises slug generation, cross-catalog keyword de-duplication, partial edits,
the archived-is-terminal rule, and root-key detection against a fake repository.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel.palette_catalog_service import (
    PaletteCatalogService,
    PaletteCreateCommand,
    PaletteNotFoundError,
    PaletteUpdateCommand,
    is_root_key,
    make_slug,
)
from rag_backend.domain.constants.carousel_themes import CAROUSEL_THEMES
from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models.palette import CustomPalette


class FakePaletteRepo:
    """In-memory ``PaletteRepository`` for service-level tests."""

    def __init__(self, seed: list[CustomPalette] | None = None) -> None:
        self.rows: dict[UUID, CustomPalette] = {p.id: p for p in (seed or [])}
        self.added: list[CustomPalette] = []

    async def get_by_id(self, palette_id: UUID) -> CustomPalette | None:
        return self.rows.get(palette_id)

    async def list_active(self) -> list[CustomPalette]:
        return [p for p in self.rows.values() if not p.archived]

    async def add(self, palette: CustomPalette) -> CustomPalette:
        self.rows[palette.id] = palette
        self.added.append(palette)
        return palette

    async def update(self, palette: CustomPalette) -> CustomPalette:
        self.rows[palette.id] = palette
        return palette

    async def archive(self, palette_id: UUID) -> bool:
        row = self.rows.get(palette_id)
        if row is None:
            return False
        self.rows[palette_id] = _replace_archived(row)
        return True


def _replace_archived(row: CustomPalette) -> CustomPalette:
    from dataclasses import replace

    return replace(row, archived=True)


def _custom(name: str, keywords: tuple[str, ...] = ()) -> CustomPalette:
    return CustomPalette(
        name=name,
        slug=f"{name.lower()}-slug",
        palette=Palette("#111111", "#222222", "#333333"),
        mode=PaletteMode.DARK,
        keywords=keywords,
    )


def _create_cmd(name: str, keywords: tuple[str, ...] = ()) -> PaletteCreateCommand:
    return PaletteCreateCommand(
        name=name,
        primary="#111111",
        accent="#222222",
        background="#333333",
        mode=PaletteMode.DARK,
        keywords=keywords,
        created_by="user-1",
    )


class TestSlug:
    def test_slug_is_url_safe_and_suffixed(self) -> None:
        slug = make_slug("Ocean Breeze!!", UUID(int=0xABCDEF12))
        assert slug.startswith("ocean-breeze-")
        assert "!" not in slug and " " not in slug

    def test_slug_falls_back_when_name_has_no_safe_chars(self) -> None:
        slug = make_slug("***", uuid4())
        assert slug.startswith("palette-")

    def test_reserved_name_does_not_shadow_route(self) -> None:
        # The id suffix guarantees the slug is never exactly a reserved route.
        slug = make_slug("new", uuid4())
        assert slug != "new"
        assert slug.startswith("palette-")


class TestRootDetection:
    def test_known_root_key_is_root(self) -> None:
        assert is_root_key(next(iter(CAROUSEL_THEMES))) is True

    def test_uuid_is_not_root(self) -> None:
        assert is_root_key(str(uuid4())) is False


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_persists_with_generated_slug(self) -> None:
        repo = FakePaletteRepo()
        service = PaletteCatalogService(repo)
        created = await service.create(_create_cmd("Sunset"))
        assert created.slug.startswith("sunset-")
        assert repo.added == [created]

    # Scenario: De-duplicate keywords across the active catalog
    @pytest.mark.asyncio
    async def test_create_drops_keyword_claimed_by_active_palette(self) -> None:
        repo = FakePaletteRepo([_custom("Owner", keywords=("fintech",))])
        service = PaletteCatalogService(repo)
        created = await service.create(_create_cmd("New", keywords=("fintech", "ai")))
        assert "fintech" not in created.keywords
        assert "ai" in created.keywords


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_applies_partial_fields(self) -> None:
        existing = _custom("Old")
        repo = FakePaletteRepo([existing])
        service = PaletteCatalogService(repo)
        updated = await service.update(
            existing.id, PaletteUpdateCommand(name="Renamed", primary="#abcabc")
        )
        assert updated.name == "Renamed"
        assert updated.palette.primary == "#abcabc"
        assert updated.palette.accent == existing.palette.accent

    @pytest.mark.asyncio
    async def test_update_keeps_own_keywords_not_self_deduped(self) -> None:
        existing = _custom("Self", keywords=("brandx",))
        repo = FakePaletteRepo([existing])
        service = PaletteCatalogService(repo)
        updated = await service.update(
            existing.id, PaletteUpdateCommand(keywords=("brandx", "fresh"))
        )
        assert set(updated.keywords) == {"brandx", "fresh"}

    # Scenario: Editing an unknown palette returns not found
    @pytest.mark.asyncio
    async def test_update_unknown_raises_not_found(self) -> None:
        service = PaletteCatalogService(FakePaletteRepo())
        with pytest.raises(PaletteNotFoundError):
            await service.update(uuid4(), PaletteUpdateCommand(name="x"))

    @pytest.mark.asyncio
    async def test_update_archived_raises_not_found(self) -> None:
        archived = _replace_archived(_custom("Gone"))
        repo = FakePaletteRepo([archived])
        service = PaletteCatalogService(repo)
        with pytest.raises(PaletteNotFoundError):
            await service.update(archived.id, PaletteUpdateCommand(name="x"))


class TestArchive:
    @pytest.mark.asyncio
    async def test_archive_existing_returns_true(self) -> None:
        existing = _custom("Bye")
        repo = FakePaletteRepo([existing])
        service = PaletteCatalogService(repo)
        assert await service.archive(existing.id) is True
        assert await service.list_active() == []

    @pytest.mark.asyncio
    async def test_archive_unknown_returns_false(self) -> None:
        service = PaletteCatalogService(FakePaletteRepo())
        assert await service.archive(uuid4()) is False
