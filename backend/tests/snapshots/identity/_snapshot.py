"""Golden-snapshot diff helper for Identity (auth + admin) endpoints (AE-0097).

This is the enforceable byte-identical baseline for the Phase 3 Identity
extraction. Later slices (AE-0099 / AE-0101 / AE-0102) move the auth/admin code
behind facades; this helper lets those slices assert the live response is
identical to the committed snapshot captured on the current, pre-refactor code.

Unlike the Knowledge helper (body-only), Identity responses carry security
relevant **Set-Cookie attributes** (``access_token`` / ``anon_token``:
httponly/secure/samesite/max-age) and the ``X-Agent-Origin`` header that the
refactor must preserve byte-for-byte. This helper therefore captures:

* ``status_code``
* normalized JSON ``body`` (volatile UUID/timestamp fields placeholdered)
* normalized ``cookies`` (per ``Set-Cookie``: value placeholdered because it is
  a fresh HS256 JWT each run, but every attribute kept verbatim)
* selected response ``headers`` (only the stable contract header
  ``x-agent-origin`` when present)

Volatile values (the JWT cookie value, UUID ids, timestamps) are normalized to
stable placeholders so the snapshot is deterministic, while still asserting the
field/attribute is present and well-formed.
"""

from __future__ import annotations

import json
import re
from http.cookies import SimpleCookie
from pathlib import Path
from typing import TYPE_CHECKING, Final
from uuid import UUID

if TYPE_CHECKING:
    from httpx import Response

# --- Placeholders for normalized volatile values --------------------------------
PLACEHOLDER_UUID: Final = "<uuid>"
PLACEHOLDER_TIMESTAMP: Final = "<timestamp>"
PLACEHOLDER_JWT: Final = "<jwt>"
PLACEHOLDER_TEMP_PASSWORD: Final = "<temp-password>"

# --- Volatile field names (normalized regardless of nesting depth) --------------
VOLATILE_UUID_FIELDS: Final[frozenset[str]] = frozenset({
    "id",
    "document_id",
    "conversation_id",
})
VOLATILE_TIMESTAMP_FIELDS: Final[frozenset[str]] = frozenset({
    "created_at",
    "updated_at",
})
# Generated secrets (admin create/reset) change every run; the contract is the
# field's presence and that it is a non-empty string, not its exact value.
VOLATILE_SECRET_FIELDS: Final[frozenset[str]] = frozenset({
    "temp_password",
    "access_token",
})

# Cookie names whose value is a fresh JWT each run (normalized to PLACEHOLDER_JWT).
JWT_COOKIE_NAMES: Final[frozenset[str]] = frozenset({"access_token", "anon_token"})

# Only this response header is part of the deterministic contract under test.
SNAPSHOT_HEADER_NAMES: Final[tuple[str, ...]] = ("x-agent-origin",)

_SNAPSHOT_DIR: Final = Path(__file__).parent

_ISO_TIMESTAMP_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

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
    if key in VOLATILE_SECRET_FIELDS and isinstance(value, str) and value:
        return PLACEHOLDER_TEMP_PASSWORD
    return normalize(value)


def normalize(body: JsonValue) -> JsonValue:
    """Recursively replace volatile field values with stable placeholders."""
    if isinstance(body, dict):
        return {key: _normalize_field(key, value) for key, value in body.items()}
    if isinstance(body, list):
        return [normalize(item) for item in body]
    return body


def _normalize_cookies(response: Response) -> dict[str, JsonValue]:
    """Capture every Set-Cookie as ``{name: {attribute: value}}``.

    The cookie value itself is a fresh JWT each run so it is placeholdered for
    JWT cookies; ALL attributes (httponly, secure, samesite, max-age, path) are
    kept verbatim because they are the security contract the refactor must
    preserve byte-for-byte.
    """
    cookies: dict[str, JsonValue] = {}
    for raw in response.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(raw)
        for name, morsel in parsed.items():
            value = PLACEHOLDER_JWT if name in JWT_COOKIE_NAMES else morsel.value
            attributes: dict[str, JsonValue] = {"value": value}
            for attr_key in ("httponly", "secure", "samesite", "max-age", "path"):
                attr_value = morsel[attr_key]
                if attr_value != "":
                    attributes[attr_key] = (
                        True if attr_value is True else str(attr_value)
                    )
            cookies[name] = attributes
    return cookies


def _snapshot_headers(response: Response) -> dict[str, JsonValue]:
    """Capture only the deterministic contract headers that are present."""
    headers: dict[str, JsonValue] = {}
    for name in SNAPSHOT_HEADER_NAMES:
        if name in response.headers:
            headers[name] = response.headers[name]
    return headers


def snapshot_path(name: str) -> Path:
    """Return the committed snapshot file path for the given endpoint name."""
    return _SNAPSHOT_DIR / f"{name}.json"


def build_snapshot(response: Response) -> dict[str, JsonValue]:
    """Build a normalized snapshot (status + body + cookies + headers)."""
    body: JsonValue
    if response.status_code == 204 or not response.content:
        body = None
    else:
        body = json.loads(response.content)
    return {
        "status_code": response.status_code,
        "body": normalize(body),
        "cookies": _normalize_cookies(response),
        "headers": _snapshot_headers(response),
    }


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
