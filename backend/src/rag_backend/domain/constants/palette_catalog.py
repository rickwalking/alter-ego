"""Validation rules + limits for the custom-palette CRUD catalog (AE-0270).

Pure constants (stdlib only) shared by the API schemas, the application catalog
service, and their tests. The colour fields are interpolated into the LLM image
prompt, so the hex pattern is a **strict** ``#rrggbb`` allow-list (prompt-injection
guard, skeptical G5); keywords feed AUTO detection, so they are capped, sanitised,
de-duplicated, and rejected when they collide with a root brand keyword (G5).
"""

from __future__ import annotations

import re

# --- Colour (strict #rrggbb; the only shape allowed into the image prompt) ---
HEX_COLOUR_PATTERN: str = r"^#[0-9a-fA-F]{6}$"
HEX_COLOUR_RE: re.Pattern[str] = re.compile(HEX_COLOUR_PATTERN)

# --- Name / slug ---
NAME_MIN_LEN: int = 1
NAME_MAX_LEN: int = 80  # matches PaletteModel.name String(80)
SLUG_MAX_LEN: int = 80
SLUG_ID_SUFFIX_LEN: int = 8  # hex chars of the UUID appended for global uniqueness
SLUG_CHAR_PATTERN: str = r"[^a-z0-9]+"  # everything else collapses to a hyphen
SLUG_CHAR_RE: re.Pattern[str] = re.compile(SLUG_CHAR_PATTERN)
# Characters that have no place in a display name and are the obvious XSS vector.
NAME_FORBIDDEN_CHARS: tuple[str, ...] = ("<", ">")
# Slugs that would shadow a sub-route under the catalog prefix.
RESERVED_SLUGS: frozenset[str] = frozenset({"new", "edit", "create", "catalog"})

# --- Keywords (AUTO-detection pool; sanitised, never rendered into a prompt) ---
KEYWORD_MAX_COUNT: int = 10
KEYWORD_MAX_LEN: int = 30

# --- Error detail strings (stable contract for the 4xx bodies + tests) ---
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
