"""Golden-snapshot diff helper for the Knowledge (documents + search) endpoints.

This is the enforceable byte-identical baseline for the Phase 2 Knowledge
extraction (AE-0088). Later slices (AE-0092 / AE-0093) relocate the
``/api/documents`` and ``/api/search`` code; this helper lets those slices
assert the live response (status code + JSON body) is identical to the
committed snapshot captured on the current, pre-refactor code.

Volatile fields (UUID ids, ``created_at`` / ``updated_at`` timestamps) are
normalized deterministically so the snapshot is stable across runs. A field is
"volatile" because its value changes every run even though the contract does
not; normalization replaces such values with a stable placeholder while still
asserting the field is present and well-formed (a UUID stays a UUID, a
timestamp stays an ISO-8601 string).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final
from uuid import UUID

if TYPE_CHECKING:
    from httpx import Response

# --- Placeholders for normalized volatile values --------------------------------
PLACEHOLDER_UUID: Final = "<uuid>"
PLACEHOLDER_TIMESTAMP: Final = "<timestamp>"
PLACEHOLDER_NUMBER: Final = "<number>"

# --- Volatile field names (normalized regardless of nesting depth) --------------
VOLATILE_UUID_FIELDS: Final[frozenset[str]] = frozenset({
    "id",
    "document_id",
    "chunk_id",
})
VOLATILE_TIMESTAMP_FIELDS: Final[frozenset[str]] = frozenset({
    "created_at",
    "updated_at",
})
# Float scores from the retriever are non-deterministic; the contract is the
# field's presence and numeric type, not the exact value.
VOLATILE_NUMBER_FIELDS: Final[frozenset[str]] = frozenset({"score"})

_SNAPSHOT_DIR: Final = Path(__file__).parent

_ISO_TIMESTAMP_RE: Final = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"  # date + time
)

# Type alias for any JSON value (Python 3.11-compatible recursive alias).
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


def _is_uuid(value: object) -> bool:
    """Return True when value is a string that parses as a UUID."""
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _is_iso_timestamp(value: object) -> bool:
    """Return True when value looks like an ISO-8601 datetime string."""
    return isinstance(value, str) and bool(_ISO_TIMESTAMP_RE.match(value))


def _normalize_field(key: str, value: JsonValue) -> JsonValue:
    """Normalize a single volatile field value, or recurse otherwise."""
    if key in VOLATILE_UUID_FIELDS and _is_uuid(value):
        return PLACEHOLDER_UUID
    if key in VOLATILE_TIMESTAMP_FIELDS and _is_iso_timestamp(value):
        return PLACEHOLDER_TIMESTAMP
    if key in VOLATILE_NUMBER_FIELDS and isinstance(value, int | float):
        return PLACEHOLDER_NUMBER
    return normalize(value)


def normalize(body: JsonValue) -> JsonValue:
    """Recursively replace volatile field values with stable placeholders."""
    if isinstance(body, dict):
        return {key: _normalize_field(key, value) for key, value in body.items()}
    if isinstance(body, list):
        return [normalize(item) for item in body]
    return body


def snapshot_path(name: str) -> Path:
    """Return the committed snapshot file path for the given endpoint name."""
    return _SNAPSHOT_DIR / f"{name}.json"


def build_snapshot(response: Response) -> dict[str, JsonValue]:
    """Build a normalized snapshot dict (status + body) from a live response."""
    body: JsonValue
    if response.status_code == 204 or not response.content:
        body = None
    else:
        body = json.loads(response.content)
    return {"status_code": response.status_code, "body": normalize(body)}


def write_snapshot(name: str, response: Response) -> None:
    """Capture and commit a snapshot for the given endpoint from a live response."""
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
    """Return a list of human-readable differences (empty list == byte-identical).

    Compares the normalized live response against the committed snapshot. The
    refactor passes when this returns ``[]`` (diff == 0).
    """
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
