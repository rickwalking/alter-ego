"""Slide data extraction helpers for editorial distribution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    DEFAULT_UNTITLED_SLIDE_LABEL,
    LONG_FORM_NOTES_KEY,
    OUTLINE_LEGACY_BODY_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
    SLIDE_DRAFT_TEXT_KEY,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_TITLE,
)
from rag_backend.application.services.carousel.types import SlideData


@dataclass(frozen=True)
class SlideDataFromDraftInput:
    """Input bundle for extracting SlideData from a draft."""

    draft: dict[str, object]
    slide_number: int
    slide_type: str
    translations_en: Mapping[int, dict[str, object]]


def _slide_heading(slide: dict[str, object]) -> str:
    presentation_pt = as_dict(slide.get(PRESENTATION_PT_KEY))
    if presentation_pt is not None:
        heading = str(presentation_pt.get("heading") or "").strip()
        if heading:
            return heading
    title = str(slide.get(OUTLINE_FIELD_TITLE, "") or "").strip()
    if title:
        return title
    legacy = str(slide.get(OUTLINE_LEGACY_HEADING_KEY, "") or "").strip()
    if legacy:
        return legacy
    return DEFAULT_UNTITLED_SLIDE_LABEL


def _slide_body(slide: dict[str, object]) -> str:
    presentation_pt = as_dict(slide.get(PRESENTATION_PT_KEY))
    if presentation_pt is not None:
        body = str(presentation_pt.get("body") or "").strip()
        if body and not body.startswith("{"):
            return body
    draft_body = str(
        slide.get(SLIDE_DRAFT_TEXT_KEY, "") or slide.get(OUTLINE_LEGACY_BODY_KEY, "")
    ).strip()
    if draft_body and not draft_body.startswith("{"):
        return draft_body
    return ""


def _slide_image_prompt(slide: dict[str, object], *, heading: str) -> str:
    raw = slide.get("image_prompt")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return f"Editorial illustration for carousel slide: {heading}"


def _structured_from_presentation(
    presentation: dict[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key in ("features", "stats", "insight", "summary_points", "tldr_strip"):
        value = presentation.get(key)
        if value is not None:
            payload[key] = value
    actions = presentation.get("actions")
    if isinstance(actions, list) and actions:
        payload["features"] = actions
    return payload


def _slide_data_from_draft(
    input: SlideDataFromDraftInput,  # noqa: A002 — shadowing built-in is intentional here
) -> SlideData:
    presentation_pt = as_dict(input.draft.get(PRESENTATION_PT_KEY)) or {}
    presentation_en = as_dict(input.draft.get(PRESENTATION_EN_KEY))
    heading = _slide_heading(input.draft)
    body = _slide_body(input.draft)
    structured_pt = _structured_from_presentation(presentation_pt)
    translation_en = input.translations_en.get(input.slide_number)
    if translation_en is None and presentation_en is not None:
        translation_en = {
            "heading": str(presentation_en.get("heading") or ""),
            "body": str(presentation_en.get("body") or ""),
            **_structured_from_presentation(presentation_en),
        }
    return SlideData(
        slide_number=input.slide_number,
        slide_type=input.slide_type,
        heading=heading,
        body=body,
        image_prompt=_slide_image_prompt(input.draft, heading=heading),
        features=structured_pt.get("features")
        if isinstance(structured_pt.get("features"), list)
        else None,
        stats=structured_pt.get("stats")
        if isinstance(structured_pt.get("stats"), list)
        else None,
        insight=structured_pt.get("insight")
        if isinstance(structured_pt.get("insight"), dict)
        else None,
        summary_points=structured_pt.get("summary_points")
        if isinstance(structured_pt.get("summary_points"), list)
        else None,
        tldr_strip=str(structured_pt["tldr_strip"])
        if isinstance(structured_pt.get("tldr_strip"), str)
        else None,
        translation_en=translation_en,
        long_form_notes=_slide_long_form_notes(input.draft),
    )


def _slide_long_form_notes(slide: dict[str, object]) -> str | None:
    raw = slide.get(LONG_FORM_NOTES_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


__all__ = [
    "SlideDataFromDraftInput",
    "_slide_body",
    "_slide_data_from_draft",
    "_slide_heading",
    "_slide_image_prompt",
    "_slide_long_form_notes",
    "_structured_from_presentation",
]
