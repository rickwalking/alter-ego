#!/usr/bin/env python
"""Read-only OpenAPI artifact exporter (AE-0141).

Builds the FastAPI application via the canonical ``create_app()`` composition
root and writes its ``app.openapi()`` document to a committed artifact at
``docs/architecture/openapi.json``. The frontend schema-drift check
(``frontend/scripts/check-schema-drift.mjs``) diffs the frontend Zod schemas
against this artifact.

This is a GENERATOR script, NOT a behavior change:
- It only *reads* the schema FastAPI already builds; it adds/removes/alters no
  route, schema, or response.
- It runs with NO live external keys. ``create_app()`` uses lazy external
  clients (Pinecone/OpenAI build on first use, not at app construction), so
  ``app.openapi()`` — which walks the route/Pydantic models only — needs no
  network, DB, or secrets. The same call is exercised keyless by
  ``backend/tests/unit/test_route_snapshot.py``.

The output JSON is serialized with ``sort_keys=True`` and a trailing newline so
the artifact is byte-stable across runs and produces clean diffs.

Usage:
    uv run python backend/scripts/export_openapi.py            # write artifact
    uv run python backend/scripts/export_openapi.py --check    # fail if drifted
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

# scripts/ -> backend/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARTIFACT_PATH = _REPO_ROOT / "docs" / "architecture" / "openapi.json"

_HEADER_KEY = "x-generated-by"
_HEADER_VALUE = (
    "backend/scripts/export_openapi.py (AE-0141) — read-only FastAPI "
    "app.openapi() snapshot; do not edit by hand."
)


def _build_openapi() -> dict[str, object]:
    """Return the live FastAPI OpenAPI document (no keys / DB / network)."""
    from rag_backend.api.app import create_app

    app = create_app()
    document = cast(dict[str, object], app.openapi())
    document[_HEADER_KEY] = _HEADER_VALUE
    return document


def _serialize(document: dict[str, object]) -> str:
    """Stable, sorted JSON with a trailing newline for clean diffs."""
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    """Write (or verify) the committed OpenAPI artifact. 0 on success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artifact matches the live schema; do not write.",
    )
    args = parser.parse_args()

    serialized = _serialize(_build_openapi())

    if args.check:
        if not _ARTIFACT_PATH.exists():
            sys.stderr.write(
                f"OpenAPI artifact missing at {_ARTIFACT_PATH}. "
                "Run `uv run python backend/scripts/export_openapi.py`.\n"
            )
            return 1
        if _ARTIFACT_PATH.read_text(encoding="utf-8") != serialized:
            sys.stderr.write(
                "OpenAPI artifact is stale. The live FastAPI schema differs "
                f"from {_ARTIFACT_PATH}. Regenerate with "
                "`uv run python backend/scripts/export_openapi.py`.\n"
            )
            return 1
        sys.stdout.write(f"OpenAPI artifact up to date: {_ARTIFACT_PATH}\n")
        return 0

    _ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ARTIFACT_PATH.write_text(serialized, encoding="utf-8")
    components = cast(
        dict[str, object],
        cast(dict[str, object], json.loads(serialized)).get("components", {}),
    )
    schemas = cast(dict[str, object], components.get("schemas", {}))
    sys.stdout.write(
        f"Wrote {_ARTIFACT_PATH} ({len(schemas)} component schemas).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
