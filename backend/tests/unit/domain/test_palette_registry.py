"""Invariants for the palette registry single source of truth (AE-0266).

Gherkin: tests/features/carousel_design_refinement.feature

These guards make the bug classes from AE-0264 unrepresentable: enum/registry
drift, a light palette in the AUTO (dark) rotation pool, and desynced derived
lookup maps.
"""

import pytest

from rag_backend.domain.constants import (
    AUTO_ROTATION_THEME_KEYS,
    BRAND_KEYWORDS,
    BRAND_PALETTES,
    CAROUSEL_THEMES,
    LIGHT_THEME_KEYS,
)
from rag_backend.domain.constants.carousel_themes import PALETTE_REGISTRY
from rag_backend.domain.constants.palette_types import (
    PaletteDescriptor,
    PaletteKind,
    PaletteMode,
)
from rag_backend.domain.models import CarouselTheme

_AUTO = "auto"


@pytest.mark.unit
class TestRegistryInvariants:
    def test_keys_are_unique(self) -> None:
        keys = [d.key for d in PALETTE_REGISTRY]
        assert len(keys) == len(set(keys))

    def test_enum_matches_registry_keys(self) -> None:
        # The CarouselTheme enum is hand-written; this guard fails CI if a
        # palette is added to the registry without its enum member (or vice
        # versa) — the AE-0264 drift class.
        enum_keys = {t.value for t in CarouselTheme} - {_AUTO}
        registry_keys = {
            d.key for d in PALETTE_REGISTRY if d.kind is not PaletteKind.BRAND
        }
        assert enum_keys == registry_keys

    def test_light_palettes_are_never_auto_selectable(self) -> None:
        for d in PALETTE_REGISTRY:
            if d.mode is PaletteMode.LIGHT:
                assert not d.auto_selectable, d.key

    def test_post_init_rejects_light_auto(self) -> None:
        with pytest.raises(ValueError, match="must not be AUTO-selectable"):
            PaletteDescriptor(
                key="bad",
                palette=PALETTE_REGISTRY[0].palette,
                mode=PaletteMode.LIGHT,
                kind=PaletteKind.VARIANT,
                auto_selectable=True,
            )


@pytest.mark.unit
class TestDerivedViews:
    def test_derived_views_match_registry(self) -> None:
        non_brand = {d.key for d in PALETTE_REGISTRY if d.kind is not PaletteKind.BRAND}
        brands = {d.key for d in PALETTE_REGISTRY if d.kind is PaletteKind.BRAND}
        assert set(CAROUSEL_THEMES) == non_brand
        assert set(BRAND_PALETTES) == brands
        assert set(BRAND_KEYWORDS) == brands
        assert set(LIGHT_THEME_KEYS) == {
            d.key for d in PALETTE_REGISTRY if d.mode is PaletteMode.LIGHT
        }
        assert set(AUTO_ROTATION_THEME_KEYS) == {
            d.key for d in PALETTE_REGISTRY if d.auto_selectable
        }

    def test_auto_pool_is_dark_categories_only(self) -> None:
        for key in AUTO_ROTATION_THEME_KEYS:
            d = next(x for x in PALETTE_REGISTRY if x.key == key)
            assert d.mode is PaletteMode.DARK
            assert d.kind is PaletteKind.CATEGORY
