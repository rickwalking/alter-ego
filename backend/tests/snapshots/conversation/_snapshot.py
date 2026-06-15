"""Golden-snapshot diff helper for Conversation endpoints (AE-0097).

The enforceable byte-identical baseline for the Phase 3 Conversation extraction.
Conversation responses carry the anonymous-visitor ``anon_token`` Set-Cookie
(httponly/secure/samesite/max-age) and the non-stream ``/chat`` route's
``X-Agent-Origin`` header — both part of the contract the refactor must
preserve. The normalization/diff logic is shared with the Identity helper
(``tests/snapshots/identity/_snapshot``); only the snapshot directory differs,
so committed snapshots live under ``tests/snapshots/conversation/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tests.snapshots.identity._snapshot import JsonValue, build_snapshot

if TYPE_CHECKING:
    from httpx import Response

# Re-export the normalization primitives so this module is the single import
# surface for conversation snapshot tests (mirrors the Knowledge helper).
__all__ = [
    "assert_matches_snapshot",
    "build_snapshot",
    "diff_snapshot",
    "load_snapshot",
    "snapshot_path",
    "write_snapshot",
]

_SNAPSHOT_DIR: Final = Path(__file__).parent


def snapshot_path(name: str) -> Path:
    """Return the committed snapshot file path for the given endpoint name."""
    return _SNAPSHOT_DIR / f"{name}.json"


def write_snapshot(name: str, response: Response) -> None:
    """Capture and commit a snapshot for the given endpoint from a response."""
    snapshot = build_snapshot(response)
    snapshot_path(name).write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_snapshot(name: str) -> dict[str, JsonValue]:
    """Load a committed snapshot by endpoint name."""
    raw: JsonValue = json.loads(snapshot_path(name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def diff_snapshot(name: str, response: Response) -> list[str]:
    """Return human-readable differences (empty list == byte-identical)."""
    expected = load_snapshot(name)
    actual = build_snapshot(response)
    if expected == actual:
        return []
    return [
        f"snapshot '{name}' mismatch:\n"
        f"  expected: {json.dumps(expected, sort_keys=True)}\n"
        f"  actual:   {json.dumps(actual, sort_keys=True)}"
    ]


def assert_matches_snapshot(name: str, response: Response) -> None:
    """Assert the live response matches the committed snapshot (diff == 0)."""
    differences = diff_snapshot(name, response)
    assert not differences, "\n".join(differences)
