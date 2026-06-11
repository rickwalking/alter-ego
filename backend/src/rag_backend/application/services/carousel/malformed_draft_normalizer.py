"""Normalize slide drafts when LLM output embeds bilingual dicts in draft_text."""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from typing import TypedDict

from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_TITLE,
    canonical_slide_type,
)
from rag_backend.domain.constants.carousel_workflow import SLIDE_DRAFT_TEXT_KEY


class LocaleBuildContext(TypedDict):
    """Parameters for building a locale presentation from a blob."""

    slide_type: str
    locale_data: Mapping[str, object]
    tldr_strip: str | None
    icon_offset: int


PRESENTATION_PT_KEY = "presentation_pt"
PRESENTATION_EN_KEY = "presentation_en"
SUMMARY_ICONS = ("brain", "target", "shield-check")
ACTION_ICONS = ("target", "flask-conical", "brain", "shield-check")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _as_mapping(value: object) -> dict[str, object] | None:
    return value if isinstance(value, Mapping) else None


def parse_bilingual_draft_blob(raw: object) -> dict[str, object] | None:
    """Parse a stringified or nested bilingual draft payload."""
    if isinstance(raw, dict):
        return dict(raw) if ("pt" in raw or "en" in raw) else None
    if not isinstance(raw, str) or not raw.strip():
        return None
    stripped = raw.strip()
    if not stripped.startswith("{") or (
        "'pt'" not in stripped and '"pt"' not in stripped
    ):
        return None
    try:
        parsed = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return None
    return dict(parsed) if isinstance(parsed, dict) else None


def _feature_item(item: Mapping[str, object], *, default_icon: str) -> dict[str, str]:
    icon = item.get("icon_name")
    return {
        "icon_name": (
            str(icon).strip()
            if isinstance(icon, str) and icon.strip()
            else default_icon
        ),
        "title": str(item.get("title") or ""),
        "body": str(item.get("body") or ""),
    }


def _strip_html(text: str) -> str:
    return _HTML_TAG_PATTERN.sub("", text).strip()


def _intro_en_tldr_fallback(en_body: str) -> str:
    plain = _strip_html(en_body)
    if not plain:
        return ""
    sentence = plain.split(".")[0].strip()
    return sentence[:120]


def build_locale_presentation_from_blob(
    context: LocaleBuildContext,
) -> dict[str, object]:
    """Build one locale presentation payload from parsed bilingual blob data."""
    slide_type = context["slide_type"]
    locale_data = context["locale_data"]
    tldr_strip = context["tldr_strip"]
    icon_offset = context["icon_offset"]
    if slide_type == "intro":
        payload: dict[str, object] = {
            "slide_type": "intro",
            "heading": str(locale_data.get("heading") or ""),
            "body": str(locale_data.get("subtitle") or locale_data.get("body") or ""),
        }
        if tldr_strip:
            payload["tldr_strip"] = tldr_strip
        return payload

    if slide_type == "summary":
        raw_points = (
            locale_data.get("points") or locale_data.get("summary_points") or []
        )
        points = (
            [item for item in raw_points if isinstance(item, Mapping)]
            if isinstance(raw_points, list)
            else []
        )
        return {
            "slide_type": "summary",
            "heading": str(locale_data.get("heading") or ""),
            "body": "",
            "summary_points": [
                _feature_item(
                    point,
                    default_icon=SUMMARY_ICONS[
                        (icon_offset + index) % len(SUMMARY_ICONS)
                    ],
                )
                for index, point in enumerate(points[:3])
            ],
        }

    if slide_type == "content":
        raw_features = locale_data.get("features") or []
        features = (
            [item for item in raw_features if isinstance(item, Mapping)]
            if isinstance(raw_features, list)
            else []
        )
        return {
            "slide_type": "content",
            "heading": str(locale_data.get("heading") or ""),
            "body": str(locale_data.get("body") or ""),
            "content_kind": "features",
            "features": [
                _feature_item(
                    feature,
                    default_icon=SUMMARY_ICONS[
                        (icon_offset + index) % len(SUMMARY_ICONS)
                    ],
                )
                for index, feature in enumerate(features[:3])
            ],
        }

    if slide_type == "closing":
        raw_actions = locale_data.get("actions") or locale_data.get("features") or []
        actions = (
            [item for item in raw_actions if isinstance(item, Mapping)]
            if isinstance(raw_actions, list)
            else []
        )
        return {
            "slide_type": "closing",
            "heading": str(locale_data.get("heading") or ""),
            "body": str(locale_data.get("body") or ""),
            "actions": [
                _feature_item(
                    action,
                    default_icon=ACTION_ICONS[
                        (icon_offset + index) % len(ACTION_ICONS)
                    ],
                )
                for index, action in enumerate(actions[:4])
            ],
        }

    return {
        "slide_type": "cta",
        "heading": str(locale_data.get("title") or locale_data.get("heading") or ""),
        "body": str(locale_data.get("body") or ""),
        "creator_name": str(
            locale_data.get("cta_creator_name") or locale_data.get("creator_name") or ""
        ),
        "creator_handle": str(
            locale_data.get("cta_handle") or locale_data.get("creator_handle") or ""
        ),
        "creator_website": str(
            locale_data.get("cta_website") or locale_data.get("creator_website") or ""
        ),
    }


def _resolve_slide_type(slide: Mapping[str, object], slide_index: int) -> str:
    raw = slide.get("slide_type") or slide.get("type")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return canonical_slide_type(slide_index)


def _has_valid_presentations(slide: Mapping[str, object]) -> bool:
    presentation_pt = _as_mapping(slide.get(PRESENTATION_PT_KEY))
    presentation_en = _as_mapping(slide.get(PRESENTATION_EN_KEY))
    if presentation_pt is None or presentation_en is None:
        return False
    pt_heading = str(presentation_pt.get("heading") or "").strip()
    pt_body = str(presentation_pt.get("body") or "").strip()
    return not (not pt_heading and pt_body.startswith("{"))


def _resolve_tldr_value(slide: dict[str, object]) -> str | None:
    """Resolve tldr_strip from slide, returning stripped value or None."""
    tldr_strip = slide.get("tldr_strip")
    if isinstance(tldr_strip, str) and tldr_strip.strip():
        return tldr_strip.strip()
    return None


def _apply_tldr_fallback(
    slide_type: str,
    tldr_value: str | None,
    presentation_en: dict[str, object],
) -> None:
    """Apply intro EN tldr fallback if the tldr_strip is empty."""
    if slide_type != "intro" or not tldr_value or presentation_en.get("tldr_strip"):
        return
    en_body = str(presentation_en.get("body") or "")
    fallback_tldr = _intro_en_tldr_fallback(en_body)
    if fallback_tldr:
        presentation_en["tldr_strip"] = fallback_tldr


def _build_updated_slide(
    slide: dict[str, object],
    presentations: tuple[dict[str, object], dict[str, object]],
    *,
    image_prompt: str,
) -> dict[str, object]:
    """Build the updated slide dict with normalized fields."""
    presentation_pt, presentation_en = presentations
    updated = dict(slide)
    updated.update({
        OUTLINE_FIELD_TITLE: str(presentation_pt.get("heading") or ""),
        PRESENTATION_PT_KEY: presentation_pt,
        PRESENTATION_EN_KEY: presentation_en,
        SLIDE_DRAFT_TEXT_KEY: str(presentation_pt.get("body") or ""),
    })
    if image_prompt:
        updated["image_prompt"] = image_prompt
    return updated


def normalize_slide_draft(slide: dict[str, object]) -> dict[str, object]:
    """Normalize one slide draft with embedded bilingual draft_text blobs."""
    if _has_valid_presentations(slide):
        return slide

    parsed = parse_bilingual_draft_blob(slide.get(SLIDE_DRAFT_TEXT_KEY))
    if parsed is None:
        return slide

    slide_index = int(slide.get("slide_index") or 1)
    slide_type = _resolve_slide_type(slide, slide_index)
    pt_data = _as_mapping(parsed.get("pt")) or {}
    en_data = _as_mapping(parsed.get("en")) or {}
    tldr_value = _resolve_tldr_value(slide)

    presentation_pt = build_locale_presentation_from_blob(
        LocaleBuildContext(
            slide_type=slide_type,
            locale_data=pt_data,
            tldr_strip=tldr_value if slide_type == "intro" else None,
            icon_offset=0,
        ),
    )
    presentation_en = build_locale_presentation_from_blob(
        LocaleBuildContext(
            slide_type=slide_type,
            locale_data=en_data,
            tldr_strip=None,
            icon_offset=0,
        ),
    )
    _apply_tldr_fallback(slide_type, tldr_value, presentation_en)

    image_prompt = parsed.get("image_prompt")
    if not isinstance(image_prompt, str):
        image_prompt = pt_data.get("image_prompt") or en_data.get("image_prompt")

    return _build_updated_slide(
        slide, (presentation_pt, presentation_en), image_prompt=str(image_prompt or "")
    )


def normalize_slide_drafts(
    slide_drafts: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Normalize all slide drafts in place order."""
    return [
        normalize_slide_draft(slide)
        for slide in slide_drafts
        if isinstance(slide, dict)
    ]


__all__ = [
    "LocaleBuildContext",
    "build_locale_presentation_from_blob",
    "normalize_slide_draft",
    "normalize_slide_drafts",
    "parse_bilingual_draft_blob",
]
