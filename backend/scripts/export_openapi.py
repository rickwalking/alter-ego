#!/usr/bin/env python
"""Read-only OpenAPI artifact exporter.

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

``--check`` runs in CI as the ``backend:openapi-fresh`` gate, so a backend schema
change that is not exported fails the PR. ``--artifact`` points either mode at
another file (used by the gate's own tests).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

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


def main(argv: list[str] | None = None) -> int:
    """Write (or verify) the committed OpenAPI artifact. 0 on success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artifact matches the live schema; do not write.",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=_ARTIFACT_PATH,
        help="Artifact path (default: docs/architecture/openapi.json).",
    )
    args = parser.parse_args(argv)
    artifact = cast(Path, args.artifact)

    serialized = _serialize(_build_openapi())

    if args.check:
        if not artifact.exists():
            sys.stderr.write(
                f"OpenAPI artifact missing at {artifact}. "
                "Run `uv run python backend/scripts/export_openapi.py`.\n"
            )
            return 1
        if artifact.read_text(encoding="utf-8") != serialized:
            sys.stderr.write(
                "OpenAPI artifact is stale. The live FastAPI schema differs "
                f"from {artifact}. Regenerate with "
                "`uv run python backend/scripts/export_openapi.py`.\n"
            )
            return 1
        sys.stdout.write(f"OpenAPI artifact up to date: {artifact}\n")
        return 0

    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(serialized, encoding="utf-8")
    components = cast(
        dict[str, object],
        cast(dict[str, object], json.loads(serialized)).get("components", {}),
    )
    schemas = cast(dict[str, object], components.get("schemas", {}))
    sys.stdout.write(f"Wrote {artifact} ({len(schemas)} component schemas).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
