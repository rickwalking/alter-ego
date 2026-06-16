"""Golden-snapshot diff helper for the publishing carousel surface (AE-0125).

The enforceable byte-identical baseline for Phase 6 (publishing /
blog-post CRUD / distribution / calendar / board / analytics). Phase 6 moves
the blog/publishing/distribution + read routes behind facades and adds an
additive migration + outbox; the later slices (AE-0128 / AE-0129 / AE-0131)
diff the live response against the committed baseline this module captures on
the current, pre-refactor code (diff == 0).

CRITICAL: this baseline INCLUDES the current carousel publish flow that sets
``is_public=True`` (the approval->release conflation) so AE-0128's release
command can be proven to diff to zero against it.

The normalization is shared with the Identity helper
(``tests/snapshots/identity/_snapshot``): volatile values — ``id`` / generic
UUID fields, timestamps — collapse to stable placeholders so the snapshot is
deterministic while still asserting the field is present and well-formed. The
publishing surface additionally exposes:

* generic resource UUID fields not in the auth-scoped Identity field set
  (``project_id``, ``owner_id``, ``author_id``, ``reviewer_id``);
* request-derived / row-derived ISO datetimes that are not keyed by the
  Identity timestamp field names (``event_date``, ``start``, ``end``,
  ``published_at``, ``submitted_for_review_at``, ``approved_at``,
  ``scheduled_publish_at``);
* the analytics velocity bucket ``week_start`` which is a DATE-only string
  (``YYYY-MM-DD``) anchored on ``now`` and therefore volatile.

Those collapse to stable placeholders here; the contract under test is that the
field is present + well-formed, not the per-run value. Every other byte — status
breakdowns, counts, titles, markdown, captions, languages, publish status — is
part of the API contract a refactor must preserve and is captured verbatim.

This module is the single import surface for publishing snapshot tests (mirrors
the presentation/editorial helpers). The committed snapshots live under
``tests/snapshots/publishing/``. Run with ``--snapshot-update`` (flag registered
in tests/conftest.py) to regenerate from current, pre-refactor behavior.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tests.snapshots.identity._snapshot import (
    PLACEHOLDER_TIMESTAMP,
    PLACEHOLDER_UUID,
    JsonValue,
    _is_iso_timestamp,
    _is_uuid,
)
from tests.snapshots.identity._snapshot import (
    build_snapshot as _identity_build_snapshot,
)

if TYPE_CHECKING:
    from httpx import Response

__all__ = [
    "PLACEHOLDER_DATE",
    "assert_matches_snapshot",
    "build_snapshot",
    "diff_snapshot",
    "load_snapshot",
    "snapshot_path",
    "write_snapshot",
]

_SNAPSHOT_DIR: Final = Path(__file__).parent

# Generic resource UUID fields the auth-scoped Identity normalizer does not
# target. Present across blog-post / carousel / calendar / board responses.
_EXTRA_VOLATILE_UUID_FIELDS: Final[frozenset[str]] = frozenset({
    "project_id",
    "owner_id",
    "author_id",
    "reviewer_id",
})

# ISO datetime fields not keyed by the Identity ``created_at`` / ``updated_at``
# set. ``event_date`` / ``start`` / ``end`` are request- or row-derived and
# anchored on ``now``; the publish lifecycle timestamps are set on release.
_EXTRA_VOLATILE_TIMESTAMP_FIELDS: Final[frozenset[str]] = frozenset({
    "event_date",
    "start",
    "end",
    "published_at",
    "submitted_for_review_at",
    "approved_at",
    "scheduled_publish_at",
})

# The analytics velocity bucket key is a DATE-only string (YYYY-MM-DD) anchored
# on ``now`` — volatile, but does NOT match the ISO-datetime regex (no time
# component), so it is normalized via its own field name + date matcher.
PLACEHOLDER_DATE: Final = "<date>"
_VOLATILE_DATE_FIELDS: Final[frozenset[str]] = frozenset({"week_start"})
_DATE_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_date(value: object) -> bool:
    return isinstance(value, str) and bool(_DATE_RE.match(value))


def _normalize_publishing_volatile(value: JsonValue) -> JsonValue:
    """Collapse publishing-specific volatile fields to stable placeholders."""
    if isinstance(value, dict):
        return {
            key: _normalize_publishing_field(key, inner) for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_normalize_publishing_volatile(item) for item in value]
    return value


def _normalize_publishing_field(key: str, value: JsonValue) -> JsonValue:
    """Normalize one publishing-volatile field, or recurse otherwise."""
    if key in _EXTRA_VOLATILE_UUID_FIELDS and _is_uuid(value):
        return PLACEHOLDER_UUID
    if key in _EXTRA_VOLATILE_TIMESTAMP_FIELDS and _is_iso_timestamp(value):
        return PLACEHOLDER_TIMESTAMP
    if key in _VOLATILE_DATE_FIELDS and _is_date(value):
        return PLACEHOLDER_DATE
    return _normalize_publishing_volatile(value)


def build_snapshot(response: Response) -> dict[str, JsonValue]:
    """Build a normalized snapshot, collapsing publishing-volatile fields."""
    snapshot = _identity_build_snapshot(response)
    normalized = _normalize_publishing_volatile(snapshot)
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
