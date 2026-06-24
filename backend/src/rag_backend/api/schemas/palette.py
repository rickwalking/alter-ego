"""Request/response schemas for the custom-palette catalog (AE-0270).

Security lives here (skeptical G5/G8): the three colour fields are validated as a
**strict** ``#rrggbb`` allow-list so no free text can reach the LLM image prompt;
the display name rejects the obvious XSS characters and is length-capped; keywords
are trimmed, lower-cased, de-duplicated, count/length-capped, and rejected when
they collide with a curated *root brand* keyword (which would let a custom palette
hijack brand AUTO-detection). All of these raise a 422 before any DB write.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.domain.constants.carousel_themes import BRAND_KEYWORDS
from rag_backend.domain.constants.palette_catalog import (
    ERR_INVALID_HEX,
    ERR_KEYWORD_BRAND_OVERLAP,
    ERR_KEYWORD_TOO_LONG,
    ERR_NAME_EMPTY,
    ERR_NAME_FORBIDDEN_CHAR,
    ERR_TOO_MANY_KEYWORDS,
    HEX_COLOUR_RE,
    KEYWORD_MAX_COUNT,
    KEYWORD_MAX_LEN,
    NAME_FORBIDDEN_CHARS,
    NAME_MAX_LEN,
    NAME_MIN_LEN,
)
from rag_backend.domain.constants.palette_types import PaletteMode

# Flattened union of every curated brand keyword — a custom keyword that lands in
# this set would steal a brand's AUTO match, so creation/edit rejects it.
_ROOT_BRAND_KEYWORDS: frozenset[str] = frozenset(
    keyword.lower() for keywords in BRAND_KEYWORDS.values() for keyword in keywords
)


def normalise_hex(value: str) -> str:
    """Return the lower-cased ``#rrggbb`` value, or raise if it is not strict hex."""
    candidate = value.strip()
    if HEX_COLOUR_RE.match(candidate) is None:
        raise ValueError(ERR_INVALID_HEX)
    return candidate.lower()


def normalise_name(value: str) -> str:
    """Trim the name and reject blank or angle-bracket (XSS) content."""
    candidate = value.strip()
    if not candidate:
        raise ValueError(ERR_NAME_EMPTY)
    if any(char in candidate for char in NAME_FORBIDDEN_CHARS):
        raise ValueError(ERR_NAME_FORBIDDEN_CHAR)
    return candidate


def sanitise_keywords(values: list[str]) -> list[str]:
    """Trim/lower/dedupe keywords and reject brand overlap, over-count, over-length."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        keyword = raw.strip().lower()
        if not keyword or keyword in seen:
            continue
        if len(keyword) > KEYWORD_MAX_LEN:
            raise ValueError(ERR_KEYWORD_TOO_LONG)
        if keyword in _ROOT_BRAND_KEYWORDS:
            raise ValueError(ERR_KEYWORD_BRAND_OVERLAP)
        seen.add(keyword)
        cleaned.append(keyword)
    if len(cleaned) > KEYWORD_MAX_COUNT:
        raise ValueError(ERR_TOO_MANY_KEYWORDS)
    return cleaned


class PaletteCreateRequest(BaseModel):
    """Create a custom palette. ``slug`` is server-generated (D8), never accepted;
    ``image_style`` is derived from ``mode`` (D3), never accepted."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=NAME_MIN_LEN, max_length=NAME_MAX_LEN)
    primary: str
    accent: str
    background: str
    mode: PaletteMode
    keywords: list[str] = Field(default_factory=list)

    _v_name = field_validator("name")(staticmethod(normalise_name))
    _v_hex = field_validator("primary", "accent", "background")(
        staticmethod(normalise_hex)
    )
    _v_keywords = field_validator("keywords")(staticmethod(sanitise_keywords))


class PaletteUpdateRequest(BaseModel):
    """Patch a custom palette. Every field is optional; ``slug`` is immutable, so
    its presence is rejected by ``extra="forbid"`` (D8)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None, min_length=NAME_MIN_LEN, max_length=NAME_MAX_LEN
    )
    primary: str | None = None
    accent: str | None = None
    background: str | None = None
    mode: PaletteMode | None = None
    keywords: list[str] | None = None

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str | None) -> str | None:
        return None if value is None else normalise_name(value)

    @field_validator("primary", "accent", "background")
    @classmethod
    def _check_hex(cls, value: str | None) -> str | None:
        return None if value is None else normalise_hex(value)

    @field_validator("keywords")
    @classmethod
    def _check_keywords(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else sanitise_keywords(value)


class CustomPaletteResponse(BaseModel):
    """A custom palette row as returned by the catalog + write endpoints."""

    id: UUID
    name: str
    slug: str
    primary: str
    accent: str
    background: str
    mode: str
    keywords: list[str]
    archived: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class RootPaletteResponse(BaseModel):
    """A read-only root palette projected from the typed registry."""

    key: str
    label_en: str
    label_pt: str
    mode: str
    primary: str
    accent: str
    background: str


class PaletteCatalogResponse(BaseModel):
    """The full catalog: read-only roots + active custom palettes (D1)."""

    roots: list[RootPaletteResponse]
    custom: list[CustomPaletteResponse]


__all__ = [
    "CustomPaletteResponse",
    "PaletteCatalogResponse",
    "PaletteCreateRequest",
    "PaletteUpdateRequest",
    "RootPaletteResponse",
    "normalise_hex",
    "normalise_name",
    "sanitise_keywords",
]
