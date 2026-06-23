"""Repository tests for the custom-palette catalog (AE-0269).

Feature: Custom palettes resolve and snapshot at generation
(.agent/tasks/AE-0269-custom-palette-persistence-db-backed-resolver-snapshot.md)

Exercises the persistence port against the test DB: round-trip, active listing
excluding archived, soft-delete, and slug-immutable update.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.infrastructure.database.palette_repository import (
    PostgresPaletteRepository,
)


def _palette(name: str, slug: str, *, archived: bool = False) -> CustomPalette:
    return CustomPalette(
        name=name,
        slug=slug,
        palette=Palette("#112233", "#445566", "#0a0a0a"),
        mode=PaletteMode.DARK,
        keywords=("alpha", "beta"),
        archived=archived,
        created_by="user-1",
    )


@pytest.mark.unit
class TestPaletteRepository:
    async def test_add_and_get_round_trip(self, db_session: AsyncSession) -> None:
        repo = PostgresPaletteRepository(db_session)
        created = await repo.add(_palette("Aurora", "aurora"))
        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Aurora"
        assert fetched.slug == "aurora"
        assert fetched.palette.primary == "#112233"
        assert fetched.mode is PaletteMode.DARK
        assert fetched.keywords == ("alpha", "beta")

    async def test_list_active_excludes_archived(
        self, db_session: AsyncSession
    ) -> None:
        repo = PostgresPaletteRepository(db_session)
        await repo.add(_palette("Active", "active"))
        await repo.add(_palette("Hidden", "hidden", archived=True))
        active = await repo.list_active()
        names = {p.name for p in active}
        assert "Active" in names
        assert "Hidden" not in names

    async def test_archive_soft_deletes_but_still_resolvable(
        self, db_session: AsyncSession
    ) -> None:
        repo = PostgresPaletteRepository(db_session)
        created = await repo.add(_palette("Temp", "temp"))
        assert await repo.archive(created.id) is True
        # Archived palette still resolves by id (existing carousels rely on it).
        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.archived is True

    async def test_archive_unknown_returns_false(
        self, db_session: AsyncSession
    ) -> None:
        repo = PostgresPaletteRepository(db_session)
        created = await repo.add(_palette("Keep", "keep"))
        # A different, non-existent id.
        other = CustomPalette(
            name="x",
            slug="x",
            palette=Palette("#000000", "#111111", "#222222"),
            mode=PaletteMode.DARK,
        )
        assert created.id != other.id
        assert await repo.archive(other.id) is False

    async def test_update_changes_name_not_slug(self, db_session: AsyncSession) -> None:
        repo = PostgresPaletteRepository(db_session)
        created = await repo.add(_palette("Old", "old-slug"))
        created.name = "New"
        created.slug = "attempted-new-slug"  # must be ignored (D8)
        updated = await repo.update(created)
        assert updated.name == "New"
        assert updated.slug == "old-slug"
