"""Unit tests for the palette contract projection + committed artifact (AE-0266 Ph3).

The contract is the single source of truth the frontend palette-drift gate
diffs against. These tests pin its shape, guarantee every user-selectable theme
carries both labels (so the UI dropdown is never label-less), exclude brand
palettes (auto-detected, never offered in the UI), and — crucially — fail if
the committed ``docs/contracts/palettes.json`` drifts from the live registries
(the staleness guard the CI ``--check`` enforces, reproduced as a unit test).
"""

import json
from pathlib import Path

import pytest

from rag_backend.application.services.carousel.palette_contract import (
    PaletteContract,
    build_palette_contract,
)
from rag_backend.domain.constants.carousel_themes import PALETTE_REGISTRY
from rag_backend.domain.constants.palette_types import PaletteKind

# backend/tests/unit/application/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ARTIFACT_PATH = _REPO_ROOT / "docs" / "contracts" / "palettes.json"


def _serialize(contract: PaletteContract) -> str:
    """Mirror export_palettes.py serialization for a byte-exact comparison."""
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


@pytest.mark.unit
class TestPaletteContract:
    def test_themes_are_every_non_brand_row(self) -> None:
        themes = build_palette_contract()["themes"]
        expected_keys = [
            d.key for d in PALETTE_REGISTRY if d.kind is not PaletteKind.BRAND
        ]
        assert [t["key"] for t in themes] == expected_keys

    def test_brands_are_excluded(self) -> None:
        theme_keys = {t["key"] for t in build_palette_contract()["themes"]}
        brand_keys = {d.key for d in PALETTE_REGISTRY if d.kind is PaletteKind.BRAND}
        assert brand_keys
        assert theme_keys.isdisjoint(brand_keys)

    def test_every_theme_has_both_labels(self) -> None:
        # A label-less FE dropdown row is the failure this guards against.
        for theme in build_palette_contract()["themes"]:
            assert theme["label_en"], f"{theme['key']} missing label_en"
            assert theme["label_pt"], f"{theme['key']} missing label_pt"

    def test_image_presets_are_sorted_pairs(self) -> None:
        presets = build_palette_contract()["image_presets"]
        pairs = [(p["model"], p["style"]) for p in presets]
        assert pairs == sorted(pairs)
        assert pairs  # non-empty

    def test_light_theme_keys_match_light_rows(self) -> None:
        contract = build_palette_contract()
        light = contract["light_theme_keys"]
        modes = {t["key"]: t["mode"] for t in contract["themes"]}
        assert set(light) == {k for k, m in modes.items() if m == "light"}

    def test_committed_artifact_is_not_stale(self) -> None:
        # Reproduces `export_palettes.py --check`: the committed file MUST equal
        # the freshly projected registries. Regenerate with
        # `uv run python backend/scripts/export_palettes.py` when the registry
        # changes.
        assert _ARTIFACT_PATH.exists(), f"missing artifact: {_ARTIFACT_PATH}"
        assert _ARTIFACT_PATH.read_text(encoding="utf-8") == _serialize(
            build_palette_contract()
        )
