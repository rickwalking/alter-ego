"""Legacy read adapters for carousel slide structured extras."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from rag_backend.domain.constants.carousel_presentation import (
    CONTENT_KIND_FEATURES,
    CONTENT_KIND_INSIGHT,
    CONTENT_KIND_STATS,
    LEGACY_STRUCTURED_EXTRA_KEYS,
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

_LEGACY_ICON_FIELD = "icon"
_ICON_NAME_FIELD = "icon_name"
_SUMMARY_POINTS_FIELD = "summary_points"
_ACTIONS_FIELD = "actions"
_STATS_FIELD = "stats"
_INSIGHT_FIELD = "insight"
_TLDR_STRIP_FIELD = "tldr_strip"
_TRANSLATION_EN_FIELD = "translation_en"
_FEATURES_FIELD = "features"
_CONTENT_KIND_FIELD = "content_kind"

# Structural signature constants
_STRUCTURAL_SIG_SUMMARY_POINTS = "summary_points"
_STRUCTURAL_SIG_ACTIONS = "actions"
_STRUCTURAL_SIG_INTRO_TLDR = "intro:tldr"
_STRUCTURAL_SIG_INTRO_PLAIN = "intro:plain"
_STRUCTURAL_SIG_INSIGHT_COUNT = "1"


def resolve_structured_item_icon_name(item: Mapping[str, object]) -> str | None:
    """Resolve icon identifier from a structured item without rewriting storage."""
    icon_name = item.get(_ICON_NAME_FIELD)
    if isinstance(icon_name, str) and icon_name.strip():
        return icon_name.strip()
    legacy_icon = item.get(_LEGACY_ICON_FIELD)
    if isinstance(legacy_icon, str) and legacy_icon.strip():
        return legacy_icon.strip()
    return None


def adapt_legacy_structured_item(item: Mapping[str, object]) -> dict[str, str]:
    """Return a read-only view of one structured item with resolved icon_name."""
    adapted: dict[str, str] = {}
    for key, value in item.items():
        if key in {_LEGACY_ICON_FIELD, _ICON_NAME_FIELD}:
            continue
        if isinstance(value, str):
            adapted[key] = value
    icon_name = resolve_structured_item_icon_name(item)
    if icon_name is not None:
        adapted[_ICON_NAME_FIELD] = icon_name
    return adapted


def adapt_legacy_structured_items(items: object) -> list[dict[str, str]] | None:
    """Adapt a legacy structured list while preserving underlying row data."""
    if not isinstance(items, list) or not items:
        return None
    adapted: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        adapted.append(adapt_legacy_structured_item(item))
    return adapted or None


def adapt_legacy_insight(insight: object) -> dict[str, str] | None:
    """Adapt a legacy insight object, resolving icon_name when present."""
    if not isinstance(insight, Mapping):
        return None
    return adapt_legacy_structured_item(insight)


_ADAPT_EXTRA_HANDLERS: dict[str, Callable[[object], object | None]] = {
    _FEATURES_FIELD: lambda v: adapt_legacy_structured_items(v),
    _SUMMARY_POINTS_FIELD: lambda v: adapt_legacy_structured_items(v),
    _STATS_FIELD: lambda v: adapt_legacy_structured_items(v),
    _INSIGHT_FIELD: lambda v: adapt_legacy_insight(v),
    _TLDR_STRIP_FIELD: lambda v: v if isinstance(v, str) else None,
}


def _adapt_extra_value(key: str, value: object) -> object | None:
    """Adapt a single extra value for a given key, or None if the key is not handled."""
    handler = _ADAPT_EXTRA_HANDLERS.get(key)
    if handler is None:
        return None
    return handler(value)


def _read_translation_en(extras: Mapping[str, object]) -> dict[str, object] | None:
    """Recursively read the translation_en nested extras, if present."""
    translation_en = extras.get(_TRANSLATION_EN_FIELD)
    if isinstance(translation_en, Mapping):
        return read_legacy_slide_extras(translation_en)
    return None


def read_legacy_slide_extras(extras: Mapping[str, object] | None) -> dict[str, object]:
    """Build a compatibility view of slide extras without mutating persisted JSON."""
    if extras is None:
        return {}
    view: dict[str, object] = {}
    for key in LEGACY_STRUCTURED_EXTRA_KEYS:
        if key not in extras:
            continue
        adapted = _adapt_extra_value(key, extras[key])
        if adapted is not None:
            view[key] = adapted
    translation_view = _read_translation_en(extras)
    if translation_view is not None:
        view[_TRANSLATION_EN_FIELD] = translation_view
    return view


def _count_list_field(payload: Mapping[str, object], field: str) -> int:
    """Return the count of items in a list field, or 0 if not a list."""
    value = payload.get(field)
    return len(value) if isinstance(value, list) else 0


_KIND_SIGNATURE_HANDLERS: dict[str, Callable[[Mapping[str, object]], str]] = {
    CONTENT_KIND_FEATURES: lambda p: (
        f"{CONTENT_KIND_FEATURES}:{_count_list_field(p, _FEATURES_FIELD)}"
    ),
    CONTENT_KIND_STATS: lambda p: (
        f"{CONTENT_KIND_STATS}:{_count_list_field(p, _STATS_FIELD)}"
    ),
    CONTENT_KIND_INSIGHT: lambda _: (
        f"{CONTENT_KIND_INSIGHT}:{_STRUCTURAL_SIG_INSIGHT_COUNT}"
    ),
}


def _content_kind_signature(payload: Mapping[str, object]) -> str | None:
    """Return structural signature from content_kind field, or None."""
    content_kind = payload.get(_CONTENT_KIND_FIELD)
    if not isinstance(content_kind, str):
        return None
    handler = _KIND_SIGNATURE_HANDLERS.get(content_kind)
    if handler is None:
        return None
    return handler(payload)


_FIELD_SIGNATURE_HANDLERS: list[tuple[str, Callable[[Mapping[str, object]], str]]] = [
    (
        _SUMMARY_POINTS_FIELD,
        lambda p: (
            f"{_STRUCTURAL_SIG_SUMMARY_POINTS}:"
            f"{_count_list_field(p, _SUMMARY_POINTS_FIELD)}"
        ),
    ),
    (
        _ACTIONS_FIELD,
        lambda p: f"{_STRUCTURAL_SIG_ACTIONS}:{_count_list_field(p, _ACTIONS_FIELD)}",
    ),
    (
        _FEATURES_FIELD,
        lambda p: f"{CONTENT_KIND_FEATURES}:{_count_list_field(p, _FEATURES_FIELD)}",
    ),
    (
        _STATS_FIELD,
        lambda p: f"{CONTENT_KIND_STATS}:{_count_list_field(p, _STATS_FIELD)}",
    ),
    (
        _INSIGHT_FIELD,
        lambda _: f"{CONTENT_KIND_INSIGHT}:{_STRUCTURAL_SIG_INSIGHT_COUNT}",
    ),
]


def structural_signature(payload: Mapping[str, object]) -> str:
    """Return a structural fingerprint used for PT/EN parity checks."""
    for field, handler in _FIELD_SIGNATURE_HANDLERS:
        if field in payload:
            return handler(payload)
    result = _content_kind_signature(payload)
    if result is not None:
        return result
    tldr = payload.get(_TLDR_STRIP_FIELD)
    if isinstance(tldr, str) and tldr.strip():
        return _STRUCTURAL_SIG_INTRO_TLDR
    return _STRUCTURAL_SIG_INTRO_PLAIN


def detect_translation_shape_mismatch(
    pt_payload: Mapping[str, object],
    en_payload: Mapping[str, object],
) -> SlideValidationViolation | None:
    """Detect PT/EN structural drift such as features vs stats."""
    pt_signature = structural_signature(pt_payload)
    en_signature = structural_signature(en_payload)
    if pt_signature == en_signature:
        return None
    return SlideValidationViolation(
        code=VIOLATION_TRANSLATION_SHAPE_MISMATCH,
        message=(
            f"PT structured shape {pt_signature!r} does not match "
            f"EN structured shape {en_signature!r}"
        ),
    )


__all__ = [
    "adapt_legacy_insight",
    "adapt_legacy_structured_item",
    "adapt_legacy_structured_items",
    "detect_translation_shape_mismatch",
    "read_legacy_slide_extras",
    "resolve_structured_item_icon_name",
    "structural_signature",
]
