"""Slide data parsing from LLM content synthesis output."""

from __future__ import annotations

from rag_backend.application.services.carousel.types import MAX_FEATURE_ITEMS, SlideData


def _parse_slides(content_data: dict[str, object]) -> list[SlideData]:
    slides_data: list[SlideData] = []
    raw_slides = content_data.get("slides", [])
    if not isinstance(raw_slides, list):
        raw_slides = []
    for slide_json in raw_slides:
        raw_features = slide_json.get("features")
        features: list[dict[str, str]] | None = None
        if isinstance(raw_features, list) and raw_features:
            features = [
                {
                    "icon": str(item.get("icon") or "✅"),
                    "title": str(item.get("title") or ""),
                    "body": str(item.get("body") or ""),
                }
                for item in raw_features[:MAX_FEATURE_ITEMS]
                if isinstance(item, dict)
            ]
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
        raw_summary_points = slide_json.get("summary_points")
        summary_points: list[dict[str, str]] | None = None
        if isinstance(raw_summary_points, list) and raw_summary_points:
            summary_points = [
                {
                    "icon": str(item.get("icon") or "🎯"),
                    "title": str(item.get("title") or ""),
                    "body": str(item.get("body") or ""),
                }
                for item in raw_summary_points[:MAX_FEATURE_ITEMS]
                if isinstance(item, dict)
            ]
        raw_tldr = slide_json.get("tldr_strip")
        tldr_strip: str | None = str(raw_tldr) if raw_tldr else None
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
            )
        )
    return slides_data
