"""Deterministic route-equality guard for the composition-root relocation.

Feature: Composition-root scaffolding (AE-0080)
  Scenario: App routes are unchanged after relocating the app factory
    Given the relocated composition root in rag_backend.bootstrap.app_factory
    When the FastAPI app is built
    Then the sorted set of path+method routes equals the committed snapshot

This is the AC "no route change" guard: the app factory moved from
``rag_backend.api.app`` to ``rag_backend.bootstrap.app_factory`` with zero
behavior change, and this test fails loudly if any route is added, removed, or
its methods change. To intentionally change routes, regenerate the snapshot
with ``REGEN_ROUTE_SNAPSHOT=1 uv run pytest tests/unit/test_route_snapshot.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI

from rag_backend.bootstrap.app_factory import create_app

SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1] / "snapshots" / "openapi_routes.json"
)

# FastAPI auto-mounts these framework routes (interactive docs + OpenAPI
# schema) and toggles them via settings, so they are present in some
# environments (local) and absent in others (CI/test profile disables docs).
# They are framework-owned, not APPLICATION routes, so the snapshot guard
# must exclude them from BOTH sides to stay environment-independent.
_FRAMEWORK_ROUTE_PATHS = frozenset({
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
})


def _is_framework_path(path: str) -> bool:
    """True for FastAPI auto-docs / OpenAPI-schema framework routes."""
    return path in _FRAMEWORK_ROUTE_PATHS or path.startswith("/openapi")


def _filter_framework_routes(entries: list[str]) -> list[str]:
    """Drop framework 'METHOD /path' entries, keeping only app routes."""
    kept: list[str] = []
    for entry in entries:
        _, _, path = entry.partition(" ")
        if _is_framework_path(path):
            continue
        kept.append(entry)
    return kept


def _extract_routes(app: FastAPI) -> list[str]:
    """Return the sorted, de-duplicated app-only 'METHOD /path' inventory."""
    entries: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path is None:
            continue
        methods = getattr(route, "methods", None)
        if methods:
            entries.extend(f"{method} {path}" for method in sorted(methods))
        else:
            entries.append(f"WEBSOCKET {path}")
    return sorted(set(_filter_framework_routes(entries)))


def test_app_routes_match_committed_snapshot() -> None:
    """The live app's routes must equal the committed snapshot byte-for-byte."""
    app = create_app()
    actual = _extract_routes(app)

    if os.environ.get("REGEN_ROUTE_SNAPSHOT") == "1":
        SNAPSHOT_PATH.write_text(json.dumps(actual, indent=2) + "\n")

    expected = _filter_framework_routes(json.loads(SNAPSHOT_PATH.read_text()))

    missing = sorted(set(expected) - set(actual))
    added = sorted(set(actual) - set(expected))
    assert actual == expected, (
        "Route inventory drifted from the committed snapshot.\n"
        f"Missing (in snapshot, not in app): {missing}\n"
        f"Added (in app, not in snapshot): {added}"
    )
