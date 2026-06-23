"""Unit tests for the generation-time palette resolver service (AE-0269).

Feature: Custom palettes resolve and snapshot at generation
(.agent/tasks/AE-0269-custom-palette-persistence-db-backed-resolver-snapshot.md)

Pure logic over a fake repository: the root + custom union, mode-derived image
style (a light palette never gets a dark strategy, D3), AUTO matching custom
keywords, and the degrade-to-registry fallback when the repo errors (G2).
"""

from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel.palette_resolver_service import (
    PaletteResolverService,
)
from rag_backend.domain.constants import (
    IMAGE_STYLE_DEFAULT,
    IMAGE_STYLE_FLAT_EDITORIAL,
)
from rag_backend.domain.constants.palette_types import Palette, PaletteMode
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.palette import CustomPalette


class _FakeRepo:
    def __init__(
        self, palettes: list[CustomPalette] | None = None, *, fail: bool = False
    ) -> None:
        self._by_id = {p.id: p for p in (palettes or [])}
        self._fail = fail

    async def get_by_id(self, palette_id: UUID) -> CustomPalette | None:
        if self._fail:
            raise RuntimeError("db down")
        return self._by_id.get(palette_id)

    async def list_active(self) -> list[CustomPalette]:
        if self._fail:
            raise RuntimeError("db down")
        return [p for p in self._by_id.values() if not p.archived]

    async def add(self, palette: CustomPalette) -> CustomPalette:
        return palette

    async def update(self, palette: CustomPalette) -> CustomPalette:
        return palette

    async def archive(self, palette_id: UUID) -> bool:
        return True


def _project(theme: str, *, topic: str = "general topic") -> CarouselProject:
    return CarouselProject(topic=topic, audience="a", niche="n", theme=theme)


def _custom(
    mode: PaletteMode, *, keywords: tuple[str, ...] = (), pid: UUID | None = None
) -> CustomPalette:
    return CustomPalette(
        id=pid or uuid4(),
        name="Custom",
        slug="custom",
        palette=Palette("#abcdef", "#123456", "#0d0d0d"),
        mode=mode,
        keywords=keywords,
    )


@pytest.mark.unit
class TestPaletteResolverService:
    async def test_custom_uuid_resolves_to_its_colours(self) -> None:
        palette = _custom(PaletteMode.DARK)
        svc = PaletteResolverService(_FakeRepo([palette]))
        resolved = await svc.resolve(_project(str(palette.id)))
        assert resolved.primary == "#abcdef"
        assert resolved.resolved_ref == str(palette.id)

    async def test_light_custom_never_gets_dark_style(self) -> None:
        palette = _custom(PaletteMode.LIGHT)
        svc = PaletteResolverService(_FakeRepo([palette]))
        resolved = await svc.resolve(_project(str(palette.id)))
        assert resolved.image_style == IMAGE_STYLE_FLAT_EDITORIAL

    async def test_dark_custom_gets_default_style(self) -> None:
        palette = _custom(PaletteMode.DARK)
        svc = PaletteResolverService(_FakeRepo([palette]))
        resolved = await svc.resolve(_project(str(palette.id)))
        assert resolved.image_style == IMAGE_STYLE_DEFAULT

    async def test_root_key_resolves_from_registry(self) -> None:
        svc = PaletteResolverService(_FakeRepo())
        resolved = await svc.resolve(_project("plasma_magenta"))
        assert resolved.resolved_ref == "plasma_magenta"
        assert set(resolved.as_snapshot("t")) >= {"primary", "accent", "background"}

    async def test_auto_matches_a_custom_keyword(self) -> None:
        palette = _custom(PaletteMode.DARK, keywords=("quantumwidget",))
        svc = PaletteResolverService(_FakeRepo([palette]))
        resolved = await svc.resolve(
            _project("auto", topic="a story about quantumwidget today")
        )
        assert resolved.resolved_ref == str(palette.id)

    async def test_auto_without_match_resolves_to_a_root_palette(self) -> None:
        svc = PaletteResolverService(_FakeRepo())
        resolved = await svc.resolve(_project("auto", topic="nondescript musings"))
        assert resolved.resolved_ref != "auto"
        assert resolved.image_style in {IMAGE_STYLE_DEFAULT, IMAGE_STYLE_FLAT_EDITORIAL}

    async def test_repo_failure_degrades_to_registry(self) -> None:
        # G2: a repo error must NOT raise; it falls back to registry resolution.
        svc = PaletteResolverService(_FakeRepo(fail=True))
        resolved = await svc.resolve(_project("auto", topic="security exploit breach"))
        assert resolved.resolved_ref  # resolved something, did not raise

    async def test_unknown_custom_uuid_falls_back_to_registry(self) -> None:
        svc = PaletteResolverService(_FakeRepo())  # empty repo
        resolved = await svc.resolve(_project(str(uuid4())))
        assert resolved.resolved_ref  # degrades to a root palette, no raise
