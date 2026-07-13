"""Integration test for theme-snapshot-at-generation (AE-0269 inc4b, D9).

Feature: Custom palettes resolve and snapshot at generation
(.agent/tasks/AE-0269-custom-palette-persistence-db-backed-resolver-snapshot.md)

Exercises ``_ensure_theme_snapshot`` (the hook the image phase calls) against the
test DB: a custom-palette project freezes its colours, the write persists, and a
second run is a no-op (idempotent). This is the wire that makes custom palettes
render — the pure render-path resolver cannot look a UUID up.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_visual_pipeline import (
    _ensure_theme_snapshot,
)
from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.palette_repository import (
    PostgresPaletteRepository,
)


@pytest.mark.unit
class TestThemeSnapshotAtGeneration:
    async def test_custom_palette_is_frozen_and_persisted(
        self, db_session: AsyncSession
    ) -> None:
        palette = await PostgresPaletteRepository(db_session).add(
            CustomPalette(
                name="Aurora",
                slug="aurora",
                palette=Palette("#ff0000", "#00ff00", "#0000ff"),
                mode=PaletteMode.LIGHT,
            )
        )
        repo = PostgresCarouselRepository(db_session)
        created = await repo.create_project(
            CarouselProject(topic="t", audience="a", niche="n", theme=str(palette.id))
        )
        assert created.theme_snapshot is None

        await _ensure_theme_snapshot(db_session, repo, created)

        assert created.theme_snapshot is not None
        assert created.theme_snapshot["primary"] == "#ff0000"
        assert created.theme_snapshot["mode"] == "light"
        # Persisted: a fresh load sees the frozen snapshot.
        reloaded = await repo.get_project_by_id(created.id)
        assert reloaded is not None
        assert reloaded.theme_snapshot is not None
        assert reloaded.theme_snapshot["primary"] == "#ff0000"

    async def test_snapshot_is_idempotent(self, db_session: AsyncSession) -> None:
        repo = PostgresCarouselRepository(db_session)
        created = await repo.create_project(
            CarouselProject(topic="t", audience="a", niche="n", theme="plasma_magenta")
        )
        await _ensure_theme_snapshot(db_session, repo, created)
        first = created.theme_snapshot
        assert first is not None
        # Second run must not re-resolve or overwrite the frozen snapshot.
        await _ensure_theme_snapshot(db_session, repo, created)
        assert created.theme_snapshot == first
