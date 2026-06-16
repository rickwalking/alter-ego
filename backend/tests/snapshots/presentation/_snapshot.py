"""Golden-snapshot diff helper for the presentation carousel surface (AE-0116).

The enforceable byte-identical baseline for Phase 5 (presentation). Phase 5
moves the presentation routes/services/persistence (design / blog / blog-i18n /
slides / strategies / creator-asset) behind a facade + ACL; later slices
(AE-0118 / AE-0120 / AE-0121) diff the live response against the committed
snapshot captured on the current, pre-refactor code (diff == 0).

The normalization is shared with the Identity / editorial helpers
(``tests/snapshots/identity/_snapshot``): volatile values — ``id``,
``project_id``, ``owner_id`` UUIDs and ``created_at`` / ``updated_at`` timestamps
— collapse to stable placeholders so the snapshot is deterministic while still
asserting the field is present and well-formed.

In ADDITION, the creator-asset upload response carries fields derived from a
WebP RE-ENCODE of the upload (``content_sha256`` and the ``relative_path`` /
``staged_relative_path`` built from that digest). The WebP encoder output is
libwebp/Pillow-version sensitive, so its sha is NOT portable across CI vs local;
those three fields are collapsed to placeholders here. The STABLE creator-asset
contract (``media_type``, ``width``, ``height``) stays byte-identical in the
snapshot, and the dedicated upload test additionally asserts those exact values.

Unlike the SSE-stream contract, the design / blog / slides / strategies /
creator-asset responses are deterministic JSON whose every byte is part of the
API contract a refactor must preserve. The FileResponse endpoints (PDF / JPEG)
are NOT JSON; their content-type, headers and byte content are asserted in the
test module via a stable sha256 digest, not through this JSON helper.

This module is the single import surface for presentation snapshot tests
(mirrors the editorial helper). The committed snapshots live under
``tests/snapshots/presentation/``. Run with ``--snapshot-update`` (flag
registered in tests/conftest.py) to regenerate from current behavior.
"""

from __future__ import annotations

import json
import re
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

__all__ = [
    "PLACEHOLDER_DERIVED_PATH",
    "PLACEHOLDER_DIGEST",
    "assert_matches_snapshot",
    "build_snapshot",
    "diff_snapshot",
    "load_snapshot",
    "snapshot_path",
    "write_snapshot",
]

_SNAPSHOT_DIR: Final = Path(__file__).parent

# Presentation responses carry a volatile ``project_id`` / ``owner_id`` UUID that
# the shared Identity normalizer does not target (its field set is auth-scoped).
_EXTRA_VOLATILE_UUID_FIELDS: Final[frozenset[str]] = frozenset({
    "project_id",
    "owner_id",
})

# Creator-asset fields derived from a WebP RE-ENCODE (libwebp/Pillow-version
# sensitive). The contract is that they are present + well-formed, not the exact
# (non-portable) digest value, so they collapse to a placeholder.
PLACEHOLDER_DIGEST: Final = "<sha256>"
PLACEHOLDER_DERIVED_PATH: Final = "<derived-path>"
_VOLATILE_DIGEST_FIELDS: Final[frozenset[str]] = frozenset({"content_sha256"})
_VOLATILE_DERIVED_PATH_FIELDS: Final[frozenset[str]] = frozenset({
    "relative_path",
    "staged_relative_path",
})

# The design/blog responses embed the volatile ``project_id`` UUID INSIDE URL
# path strings (``/api/carousels/<uuid>/slide-images/...``). Those values are
# not keyed by ``project_id`` so the field-name normalizer never reaches them;
# collapse any embedded UUID substring to the placeholder so the artifact-URL
# baseline asserts the URL SHAPE byte-for-byte without pinning the per-run UUID.
_EMBEDDED_UUID_RE: Final = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _normalize_presentation_volatile(value: JsonValue) -> JsonValue:
    """Collapse presentation-specific volatile fields to stable placeholders."""
    if isinstance(value, dict):
        return {
            key: _normalize_presentation_field(key, inner)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_normalize_presentation_volatile(item) for item in value]
    if isinstance(value, str):
        return _EMBEDDED_UUID_RE.sub(PLACEHOLDER_UUID, value)
    return value


def _normalize_presentation_field(key: str, value: JsonValue) -> JsonValue:
    """Normalize one presentation-volatile field, or recurse otherwise."""
    if key in _EXTRA_VOLATILE_UUID_FIELDS and _is_uuid(value):
        return PLACEHOLDER_UUID
    if key in _VOLATILE_DIGEST_FIELDS and isinstance(value, str) and value:
        return PLACEHOLDER_DIGEST
    if key in _VOLATILE_DERIVED_PATH_FIELDS and isinstance(value, str) and value:
        return PLACEHOLDER_DERIVED_PATH
    return _normalize_presentation_volatile(value)


def build_snapshot(response: Response) -> dict[str, JsonValue]:
    """Build a normalized snapshot, collapsing presentation-volatile fields."""
    snapshot = _identity_build_snapshot(response)
    normalized = _normalize_presentation_volatile(snapshot)
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
