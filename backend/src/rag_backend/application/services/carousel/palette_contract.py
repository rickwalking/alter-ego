"""Palette contract — the registry projected to a frontend-facing artifact.

The backend ``PALETTE_REGISTRY`` (themes + labels + light/dark mode) and
``IMAGE_STRATEGY_REGISTRY`` (the supported ``(model, style)`` presets) are the
single source of truth. This module projects them into a plain, serializable
``dict`` that ``backend/scripts/export_palettes.py`` writes to
``docs/contracts/palettes.json``. The frontend ``check-palette-drift.mjs`` gate
diffs the create-form constants + i18n labels against that artifact, so the
dropdown, the zod preset enum, and the locale labels can no longer silently
desync from the backend (AE-0266 Phase 3 — the FE-missed-a-theme class of the
AE-0264 bugs).
"""

from __future__ import annotations

from rag_backend.application.services.image_style_strategies import (
    IMAGE_STRATEGY_REGISTRY,
)
from rag_backend.domain.constants.carousel_themes import PALETTE_REGISTRY
from rag_backend.domain.constants.palette_types import PaletteKind, PaletteMode

CONTRACT_GENERATOR = "backend/scripts/export_palettes.py"
CONTRACT_NOTE = (
    "Generated from PALETTE_REGISTRY + IMAGE_STRATEGY_REGISTRY (AE-0266). "
    "Do not edit by hand; run the generator and commit the result."
)


def _theme_rows() -> list[dict[str, str]]:
    """User-selectable themes (every non-brand registry row), in registry order.

    Brand palettes are auto-detected from keywords, never offered in the UI
    dropdown, so they are excluded from the frontend contract.
    """
    return [
        {
            "key": descriptor.key,
            "mode": descriptor.mode.value,
            "kind": descriptor.kind.value,
            "label_en": descriptor.label_en,
            "label_pt": descriptor.label_pt,
        }
        for descriptor in PALETTE_REGISTRY
        if descriptor.kind is not PaletteKind.BRAND
    ]


def _light_theme_keys() -> list[str]:
    """Light-background theme keys, in registry order (FE nudges to editorial)."""
    return [
        descriptor.key
        for descriptor in PALETTE_REGISTRY
        if descriptor.mode is PaletteMode.LIGHT
        and descriptor.kind is not PaletteKind.BRAND
    ]


def _image_presets() -> list[dict[str, str]]:
    """Supported ``(model, style)`` presets, sorted for a byte-stable artifact."""
    return [
        {"model": model, "style": style}
        for model, style in sorted(IMAGE_STRATEGY_REGISTRY)
    ]


def build_palette_contract() -> dict[str, object]:
    """Project the registries into the serializable frontend contract."""
    return {
        "_generator": CONTRACT_GENERATOR,
        "_note": CONTRACT_NOTE,
        "themes": _theme_rows(),
        "light_theme_keys": _light_theme_keys(),
        "image_presets": _image_presets(),
    }
