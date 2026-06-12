"""Resolve localized copy blobs and strip dash punctuation from visible text."""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping

from rag_backend.domain.constants.carousel import LANGUAGE_PT

_EM_DASH = "\u2014"
_EN_DASH = "\u2013"
_PROSE_HYPHEN_PATTERN = re.compile(r"\s-\s")
_LOCALE_PT_KEY = "pt"
_LOCALE_EN_KEY = "en"
_WHITESPACE_COLLAPSE_PATTERN = re.compile(r"\s{2,}")


def strip_dashes_from_visible_copy(text: str) -> str:
    """Remove em/en dash punctuation and spaced hyphen clause separators."""
    if not text:
        return ""
    cleaned = text.replace(_EM_DASH, ", ").replace(_EN_DASH, ", ")
    cleaned = _PROSE_HYPHEN_PATTERN.sub(", ", cleaned)
    cleaned = _WHITESPACE_COLLAPSE_PATTERN.sub(" ", cleaned)
    return cleaned.replace(", ,", ",").strip(" ,")


def _parse_stringified_mapping(raw: str) -> dict[str, object] | None:
    stripped = raw.strip()
    if not stripped.startswith("{"):
        return None
    if _LOCALE_PT_KEY not in stripped and _LOCALE_EN_KEY not in stripped:
        return None
    try:
        parsed = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return None
    return dict(parsed) if isinstance(parsed, dict) else None


def resolve_localized_string(
    value: object,
    *,
    locale: str = LANGUAGE_PT,
) -> str:
    """Return one locale string from plain text, bilingual dicts, or stringified dicts."""
    resolved = ""
    if isinstance(value, Mapping):
        for key in (locale, _LOCALE_PT_KEY, _LOCALE_EN_KEY):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                resolved = candidate.strip()
                break
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped:
            parsed = _parse_stringified_mapping(stripped)
            resolved = (
                resolve_localized_string(parsed, locale=locale)
                if parsed is not None
                else stripped
            )
    elif isinstance(value, (int, float)):
        resolved = str(value).strip()
    return resolved


def sanitize_visible_copy(
    value: object,
    *,
    locale: str = LANGUAGE_PT,
) -> str:
    """Resolve localized copy and strip dash punctuation."""
    resolved = resolve_localized_string(value, locale=locale)
    return strip_dashes_from_visible_copy(resolved)


__all__ = [
    "resolve_localized_string",
    "sanitize_visible_copy",
    "strip_dashes_from_visible_copy",
]
