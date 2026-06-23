#!/usr/bin/env python
"""Read-only palette-contract exporter (AE-0266 Phase 3).

Projects the backend ``PALETTE_REGISTRY`` + ``IMAGE_STRATEGY_REGISTRY`` into a
committed artifact at ``docs/contracts/palettes.json``. The frontend
palette-drift check (``frontend/scripts/check-palette-drift.mjs``) diffs the
create-form theme constants, the zod preset combos, and the i18n locale labels
against this artifact, so adding a palette stays a one-row registry edit that
can never silently desync the UI.

This is a GENERATOR script, NOT a behavior change: it only *reads* the
registries (pure in-process data, no network/DB/keys) and serializes them. The
output is ``sort_keys=True`` with a trailing newline so the artifact is
byte-stable across runs and diffs cleanly.

Usage:
    uv run python backend/scripts/export_palettes.py            # write artifact
    uv run python backend/scripts/export_palettes.py --check    # fail if drifted
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.palette_contract import (
        PaletteContract,
    )

# scripts/ -> backend/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARTIFACT_PATH = _REPO_ROOT / "docs" / "contracts" / "palettes.json"


def _serialize(contract: PaletteContract) -> str:
    """Stable, sorted JSON with a trailing newline for clean diffs."""
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    """Write (or verify) the committed palette contract. 0 on success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artifact matches the registries; do not write.",
    )
    args = parser.parse_args()

    # Imported lazily so `--help` works without importing the app package.
    from rag_backend.application.services.carousel.palette_contract import (
        build_palette_contract,
    )

    serialized = _serialize(build_palette_contract())

    if args.check:
        if not _ARTIFACT_PATH.exists():
            sys.stderr.write(
                f"Palette contract missing at {_ARTIFACT_PATH}. "
                "Run `uv run python backend/scripts/export_palettes.py`.\n"
            )
            return 1
        if _ARTIFACT_PATH.read_text(encoding="utf-8") != serialized:
            sys.stderr.write(
                "Palette contract is stale. The registries differ from "
                f"{_ARTIFACT_PATH}. Regenerate with "
                "`uv run python backend/scripts/export_palettes.py`.\n"
            )
            return 1
        sys.stdout.write(f"Palette contract up to date: {_ARTIFACT_PATH}\n")
        return 0

    _ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ARTIFACT_PATH.write_text(serialized, encoding="utf-8")
    contract = json.loads(serialized)
    themes = contract.get("themes", [])
    presets = contract.get("image_presets", [])
    sys.stdout.write(
        f"Wrote {_ARTIFACT_PATH} ({len(themes)} themes, {len(presets)} presets).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
