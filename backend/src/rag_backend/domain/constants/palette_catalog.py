"""Validation rules + limits for the custom-palette CRUD catalog.

Pure constants (stdlib only) shared by the API schemas, the application catalog
service, and their tests. The colour fields are interpolated into the LLM image
prompt, so the hex pattern is a **strict** ``#rrggbb`` allow-list (prompt-injection
guard); keywords feed AUTO detection, so they are capped, sanitised,
de-duplicated, never rendered into a prompt, and rejected when they collide with
a root brand keyword.

``NAME_MAX_LEN`` matches ``PaletteModel.name`` (``String(80)``). A slug gets
``SLUG_ID_SUFFIX_LEN`` hex chars of the UUID appended for global uniqueness, and
every char outside ``[a-z0-9]`` collapses to a hyphen. ``NAME_FORBIDDEN_CHARS``
are the obvious XSS vector; ``RESERVED_SLUGS`` would shadow a sub-route under the
catalog prefix. The error detail strings are a stable contract for the 4xx
bodies and tests.
"""

from __future__ import annotations

import re

HEX_COLOUR_PATTERN: str = r"^#[0-9a-fA-F]{6}$"
HEX_COLOUR_RE: re.Pattern[str] = re.compile(HEX_COLOUR_PATTERN)

NAME_MIN_LEN: int = 1
NAME_MAX_LEN: int = 80
SLUG_MAX_LEN: int = 80
SLUG_ID_SUFFIX_LEN: int = 8
SLUG_CHAR_PATTERN: str = r"[^a-z0-9]+"
SLUG_CHAR_RE: re.Pattern[str] = re.compile(SLUG_CHAR_PATTERN)
NAME_FORBIDDEN_CHARS: tuple[str, ...] = ("<", ">")
RESERVED_SLUGS: frozenset[str] = frozenset({"new", "edit", "create", "catalog"})

KEYWORD_MAX_COUNT: int = 10
KEYWORD_MAX_LEN: int = 30

ERR_INVALID_HEX: str = "colour must be a strict #rrggbb hex value"
ERR_NAME_FORBIDDEN_CHAR: str = "name must not contain angle brackets"
ERR_NAME_EMPTY: str = "name must not be blank"
ERR_KEYWORD_BRAND_OVERLAP: str = "keyword overlaps a reserved root brand keyword"
ERR_TOO_MANY_KEYWORDS: str = "too many keywords"
ERR_KEYWORD_TOO_LONG: str = "keyword exceeds the maximum length"
ERR_SLUG_UNUSABLE: str = "name does not yield a usable slug"
ERR_PALETTE_NOT_FOUND: str = "custom palette not found"
ERR_ROOT_PALETTE_IMMUTABLE: str = "root palettes are read-only"
ERR_PALETTE_NAME_CONFLICT: str = "a palette with this name already exists"

__all__ = [
    "ERR_INVALID_HEX",
    "ERR_KEYWORD_BRAND_OVERLAP",
    "ERR_KEYWORD_TOO_LONG",
    "ERR_NAME_EMPTY",
    "ERR_NAME_FORBIDDEN_CHAR",
    "ERR_PALETTE_NAME_CONFLICT",
    "ERR_PALETTE_NOT_FOUND",
    "ERR_ROOT_PALETTE_IMMUTABLE",
    "ERR_SLUG_UNUSABLE",
    "ERR_TOO_MANY_KEYWORDS",
    "HEX_COLOUR_PATTERN",
    "HEX_COLOUR_RE",
    "KEYWORD_MAX_COUNT",
    "KEYWORD_MAX_LEN",
    "NAME_FORBIDDEN_CHARS",
    "NAME_MAX_LEN",
    "NAME_MIN_LEN",
    "RESERVED_SLUGS",
    "SLUG_CHAR_PATTERN",
    "SLUG_CHAR_RE",
    "SLUG_ID_SUFFIX_LEN",
    "SLUG_MAX_LEN",
]
