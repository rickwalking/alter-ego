"""Golden-snapshot diff helper for editorial carousel workflow endpoints (AE-0106).

The enforceable byte-identical baseline for the Phase 4 carousel workflow slice
(AE-0107 / AE-0110 / AE-0111 move workflow start/state/resume + the
``carousel_projects`` writers behind editorial handlers + an ACL). This helper
lets those slices assert the live response is identical to the committed snapshot
captured on the current, pre-refactor code (diff == 0).

The normalization/diff logic is shared with the Identity helper
(``tests/snapshots/identity/_snapshot``): volatile values — the workflow
``project_id`` UUID, ``id`` fields, timestamps — collapse to stable placeholders
so the snapshot is deterministic, while still asserting the field is present and
well-formed. ONLY the snapshot directory differs, so committed editorial
snapshots live under ``tests/snapshots/editorial/``.

Unlike the SSE-stream contract (asserted structurally in the test module, never
byte-diffed against live phase/LLM content), the workflow STATE / START / RESUME
responses are deterministic JSON whose every byte is part of the API contract a
refactor must preserve — INCLUDING the artifact URL fields the state response
exposes (``image_assets`` image paths, ``blog_markdown``, ``design_applied``).
The fixtures use STABLE artifact paths (no embedded volatile UUID) so those
fields are captured verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tests.snapshots.identity._snapshot import (
    PLACEHOLDER_UUID,
    JsonValue,
    _is_uuid,
)
from tests.snapshots.identity._snapshot import (
    build_snapshot as _identity_build_snapshot,
)

if TYPE_CHECKING:
    from httpx import Response

# Re-export the normalization primitives so this module is the single import
# surface for editorial snapshot tests (mirrors the Conversation helper).
__all__ = [
    "assert_matches_snapshot",
    "build_snapshot",
    "diff_snapshot",
    "load_snapshot",
    "snapshot_path",
    "write_snapshot",
]

_SNAPSHOT_DIR: Final = Path(__file__).parent

# Workflow responses (state / resume) carry a volatile ``project_id`` UUID that
# the shared Identity normalizer does not target (its field set is auth-scoped).
# Normalize it here so the byte-identical baseline asserts the field is a
# well-formed UUID without pinning the per-run value.
_EXTRA_VOLATILE_UUID_FIELDS: Final[frozenset[str]] = frozenset({"project_id"})


def _normalize_workflow_volatile(value: JsonValue) -> JsonValue:
    """Recursively collapse the workflow ``project_id`` UUID to a placeholder."""
    if isinstance(value, dict):
        return {
            key: (
                PLACEHOLDER_UUID
                if key in _EXTRA_VOLATILE_UUID_FIELDS and _is_uuid(inner)
                else _normalize_workflow_volatile(inner)
            )
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_normalize_workflow_volatile(item) for item in value]
    return value


def build_snapshot(response: Response) -> dict[str, JsonValue]:
    """Build a normalized snapshot, also collapsing the volatile ``project_id``."""
    snapshot = _identity_build_snapshot(response)
    normalized = _normalize_workflow_volatile(snapshot)
    assert isinstance(normalized, dict)
    return normalized


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
