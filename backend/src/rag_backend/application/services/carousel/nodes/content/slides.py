"""Slide data parsing from LLM content synthesis output."""

from __future__ import annotations

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS, SlideData
from rag_backend.domain.constants.carousel_presentation import (
    DEFAULT_FEATURE_ICON_NAME,
    DEFAULT_SUMMARY_POINT_ICON_NAME,
)

_ICON_NAME_FIELD = "icon_name"
_LEGACY_ICON_FIELD = "icon"


def _resolve_icon_name(item: dict[str, object], default: str) -> str:
    raw_name = item.get(_ICON_NAME_FIELD)
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip()
    legacy_icon = item.get(_LEGACY_ICON_FIELD)
    if isinstance(legacy_icon, str) and legacy_icon.strip():
        return legacy_icon.strip()
    return default


def _parse_structured_items(
    raw_items: object,
    *,
    default_icon_name: str,
) -> list[dict[str, str]] | None:
    if not isinstance(raw_items, list) or not raw_items:
        return None
    parsed: list[dict[str, str]] = []
    for item in raw_items[:MAX_FEATURE_ITEMS]:
        if not isinstance(item, dict):
            continue
        parsed.append({
            _ICON_NAME_FIELD: _resolve_icon_name(item, default_icon_name),
            "title": str(item.get("title") or ""),
            "body": str(item.get("body") or ""),
        })
    return parsed or None


def _parse_slides(content_data: dict[str, object]) -> list[SlideData]:
    slides_data: list[SlideData] = []
    raw_slides = content_data.get("slides", [])
    if not isinstance(raw_slides, list):
        raw_slides = []
    for slide_json in raw_slides:
        features = _parse_structured_items(
            slide_json.get("features"),
            default_icon_name=DEFAULT_FEATURE_ICON_NAME,
        )
        raw_stats = slide_json.get("stats")
        stats: list[dict[str, str]] | None = None
        if isinstance(raw_stats, list) and raw_stats:
            stats = [
                {
                    "value": str(item.get("value") or ""),
                    "label": str(item.get("label") or ""),
                    "detail": str(item.get("detail") or ""),
                }
                for item in raw_stats
                if isinstance(item, dict)
            ]
        raw_insight = slide_json.get("insight")
        insight: dict[str, str] | None = None
        if isinstance(raw_insight, dict) and raw_insight.get("quote"):
            insight = {
                "quote": str(raw_insight.get("quote") or ""),
                "attribution": str(raw_insight.get("attribution") or ""),
            }
        summary_points = _parse_structured_items(
            slide_json.get("summary_points"),
            default_icon_name=DEFAULT_SUMMARY_POINT_ICON_NAME,
        )
        raw_tldr = slide_json.get("tldr_strip")
        tldr_strip: str | None = str(raw_tldr) if raw_tldr else None
        raw_notes = slide_json.get("long_form_notes")
        long_form_notes = str(raw_notes) if raw_notes else None
        slides_data.append(
            SlideData(
                slide_number=slide_json["number"],
                slide_type=slide_json["type"],
                heading=slide_json["heading"],
                body=slide_json["body"],
                image_prompt=slide_json.get("image_prompt"),
                features=features,
                stats=stats,
                insight=insight,
                summary_points=summary_points,
                tldr_strip=tldr_strip,
                long_form_notes=long_form_notes,
            )
        )
    return slides_data
