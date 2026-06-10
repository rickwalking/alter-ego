"""Legacy read adapters for carousel slide structured extras."""

from __future__ import annotations

from collections.abc import Mapping

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


def read_legacy_slide_extras(extras: Mapping[str, object] | None) -> dict[str, object]:
    """Build a compatibility view of slide extras without mutating persisted JSON."""
    if extras is None:
        return {}
    view: dict[str, object] = {}
    for key in LEGACY_STRUCTURED_EXTRA_KEYS:
        if key not in extras:
            continue
        value = extras[key]
        if key in {"features", "summary_points"}:
            adapted = adapt_legacy_structured_items(value)
            if adapted is not None:
                view[key] = adapted
            continue
        if key == "stats":
            adapted = adapt_legacy_structured_items(value)
            if adapted is not None:
                view[key] = adapted
            continue
        if key == "insight":
            adapted = adapt_legacy_insight(value)
            if adapted is not None:
                view[key] = adapted
            continue
        if key == "tldr_strip" and isinstance(value, str):
            view[key] = value
    translation_en = extras.get("translation_en")
    if isinstance(translation_en, Mapping):
        view["translation_en"] = read_legacy_slide_extras(translation_en)
    return view


def structural_signature(payload: Mapping[str, object]) -> str:
    """Return a structural fingerprint used for PT/EN parity checks."""
    if "summary_points" in payload:
        points = payload.get("summary_points")
        count = len(points) if isinstance(points, list) else 0
        return f"summary_points:{count}"
    if "actions" in payload:
        actions = payload.get("actions")
        count = len(actions) if isinstance(actions, list) else 0
        return f"actions:{count}"
    if "features" in payload:
        features = payload.get("features")
        count = len(features) if isinstance(features, list) else 0
        return f"{CONTENT_KIND_FEATURES}:{count}"
    if "stats" in payload:
        stats = payload.get("stats")
        count = len(stats) if isinstance(stats, list) else 0
        return f"{CONTENT_KIND_STATS}:{count}"
    if "insight" in payload:
        return f"{CONTENT_KIND_INSIGHT}:1"
    if "content_kind" in payload:
        content_kind = payload.get("content_kind")
        if content_kind == CONTENT_KIND_FEATURES:
            features = payload.get("features")
            count = len(features) if isinstance(features, list) else 0
            return f"{CONTENT_KIND_FEATURES}:{count}"
        if content_kind == CONTENT_KIND_STATS:
            stats = payload.get("stats")
            count = len(stats) if isinstance(stats, list) else 0
            return f"{CONTENT_KIND_STATS}:{count}"
        if content_kind == CONTENT_KIND_INSIGHT:
            return f"{CONTENT_KIND_INSIGHT}:1"
    tldr = payload.get("tldr_strip")
    if isinstance(tldr, str) and tldr.strip():
        return "intro:tldr"
    return "intro:plain"


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
