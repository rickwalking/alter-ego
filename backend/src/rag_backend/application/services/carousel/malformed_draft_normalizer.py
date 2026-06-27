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


def _locale_has_content(locale: Mapping[str, object]) -> bool:
    """Return True when a reshaped locale dict carries renderable copy."""
    return bool(
        str(locale.get("heading") or "").strip()
        or str(locale.get("body") or "").strip()
        or str(locale.get("subtitle") or "").strip()
        or locale.get("points")
        or locale.get("summary_points")
        or locale.get("features")
        or locale.get("actions")
    )


_LOCALE_SUFFIX_PT = "_pt"
_LOCALE_SUFFIX_EN = "_en"
_LOCALE_SUFFIXES = (_LOCALE_SUFFIX_PT, _LOCALE_SUFFIX_EN)
_LOCALE_SUFFIX_LEN = 3


def _has_locale_suffix(key: str) -> bool:
    return len(key) > _LOCALE_SUFFIX_LEN and key.endswith(_LOCALE_SUFFIXES)


def _localize_item(item: Mapping[str, object], suffix: str) -> dict[str, object]:
    """Resolve one structured item's locale suffix (``title_pt`` → ``title``)."""
    out: dict[str, object] = {
        key: value for key, value in item.items() if not _has_locale_suffix(key)
    }
    for key, value in item.items():
        if len(key) > _LOCALE_SUFFIX_LEN and key.endswith(suffix):
            out[key[:-_LOCALE_SUFFIX_LEN]] = value
    return out


def _localize_value(value: object, suffix: str) -> object:
    """Localize a structured-item list; pass non-item values through unchanged."""
    if isinstance(value, list) and value and all(isinstance(x, Mapping) for x in value):
        return [_localize_item(x, suffix) for x in value]
    return value


def _split_locales(
    blob: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Split a flat blob into ``(pt, en)`` dicts, suffixed keys overriding shared."""
    pt: dict[str, object] = {}
    en: dict[str, object] = {}
    for key, value in blob.items():
        if _has_locale_suffix(key):
            continue
        pt[key] = _localize_value(value, _LOCALE_SUFFIX_PT)
        en[key] = _localize_value(value, _LOCALE_SUFFIX_EN)
    for key, value in blob.items():
        if not _has_locale_suffix(key):
            continue
        suffix = key[-_LOCALE_SUFFIX_LEN:]
        target = pt if suffix == _LOCALE_SUFFIX_PT else en
        target[key[:-_LOCALE_SUFFIX_LEN]] = _localize_value(value, suffix)
    return pt, en


def _mirror_subtitle_body(locale: dict[str, object]) -> None:
    """Ensure both ``subtitle`` and ``body`` carry the copy for any builder path."""
    subtitle = str(locale.get("subtitle") or "").strip()
    body = str(locale.get("body") or "").strip()
    if subtitle and not body:
        locale["body"] = locale["subtitle"]
    elif body and not subtitle:
        locale["subtitle"] = locale["body"]


def _reshape_flat_blob(blob: Mapping[str, object]) -> dict[str, object] | None:
    """Reshape a flat draft blob into the nested ``{pt, en}`` builder shape.

    GLM emits per-slide copy as a flat dict where the locale is a key suffix
    (``heading_pt``/``subtitle_pt``/``body_en`` …) or, for single-locale clean
    slides, plain ``heading``/``body``. The bilingual builder expects nested
    ``pt``/``en`` locale dicts, so without this reshape the raw blob string was
    dumped into ``body`` and rendered as title-only slides. Suffixed keys win
    over shared ones (recursively, so ``points``/``features`` item entries with
    ``title_pt``/``body_en`` resolve per locale too), and ``subtitle``↔``body``
    are mirrored so both the intro builder (reads ``subtitle``) and the
    content/closing/cta builders (read ``body``) find the copy.
    """
    pt, en = _split_locales(blob)
    _mirror_subtitle_body(pt)
    _mirror_subtitle_body(en)
    if not _locale_has_content(pt) and not _locale_has_content(en):
        return None
    return {"pt": pt, "en": en}


def parse_bilingual_draft_blob(raw: object) -> dict[str, object] | None:
    """Parse a stringified or nested bilingual draft payload.

    Accepts the nested ``{pt, en}`` shape as-is and reshapes flat blobs (clean
    ``heading``/``body`` or locale-suffixed ``heading_pt``/``subtitle_en`` …)
    into that nested shape so GLM's varied output structures all yield body copy.
    """
    if isinstance(raw, Mapping):
        blob: dict[str, object] = dict(raw)
    elif isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = ast.literal_eval(raw.strip())
        except (SyntaxError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        blob = parsed
    else:
        return None
    if "pt" in blob or "en" in blob:
        return blob
    return _reshape_flat_blob(blob)


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
