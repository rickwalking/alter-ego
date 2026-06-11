"""Compose public blog markdown from long-form notes, outline, and research."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    LONG_FORM_NOTES_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_SLIDE_INDEX,
    OUTLINE_FIELD_TITLE,
)
from rag_backend.application.services.carousel.types import MAX_SLIDES

BLOG_SECTION_HEADING_PREFIX = "## "


@dataclass(frozen=True)
class BlogCompositionInput:
    """Inputs for building blog markdown without constrained slide bodies."""

    slides: tuple[dict[str, object], ...]
    title: str
    research_summary: str = ""
    outline: tuple[dict[str, object], ...] = ()


def _extract_long_form_note(slide: Mapping[str, object]) -> str:
    direct = slide.get(LONG_FORM_NOTES_KEY)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    extras = slide.get("extras")
    if isinstance(extras, Mapping):
        nested = extras.get(LONG_FORM_NOTES_KEY)
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return ""


def _resolve_slide_index(slide: Mapping[str, object], fallback: int) -> int:
    raw = (
        slide.get(SLIDE_INDEX_KEY)
        or slide.get(OUTLINE_FIELD_SLIDE_INDEX)
        or slide.get("number")
    )
    if isinstance(raw, int) and raw > 0:
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return fallback


def _resolve_section_heading(
    slide: Mapping[str, object],
    outline_by_index: Mapping[int, Mapping[str, object]],
) -> str:
    slide_index = _resolve_slide_index(slide, 0)
    outline_item = outline_by_index.get(slide_index)
    if outline_item is not None:
        title = outline_item.get(OUTLINE_FIELD_TITLE) or outline_item.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    for key in (OUTLINE_FIELD_TITLE, OUTLINE_LEGACY_HEADING_KEY, "heading", "title"):
        value = slide.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"Slide {slide_index}"


def _outline_index(
    outline: tuple[dict[str, object], ...],
) -> dict[int, dict[str, object]]:
    indexed: dict[int, dict[str, object]] = {}
    for index, item in enumerate(outline):
        if not isinstance(item, dict):
            continue
        slide_index = _resolve_slide_index(item, index + 1)
        indexed[slide_index] = item
    return indexed


def build_blog_markdown_from_long_form_notes(
    composition: BlogCompositionInput,
) -> str:
    """Build blog markdown from research, outline headings, and long-form notes."""
    sections: list[str] = [f"# {composition.title}", ""]
    research = composition.research_summary.strip()
    if research:
        sections.append(research)
        sections.append("")

    outline_by_index = _outline_index(composition.outline)
    for slide in composition.slides[:MAX_SLIDES]:
        if not isinstance(slide, dict):
            continue
        note = _extract_long_form_note(slide)
        if not note:
            continue
        heading = _resolve_section_heading(slide, outline_by_index)
        sections.append(f"{BLOG_SECTION_HEADING_PREFIX}{heading}")
        sections.append("")
        sections.append(note)
        sections.append("")

    return "\n".join(sections).strip()


def _resolve_en_slide_content(
    slide: dict[str, object],
    translations_en: Mapping[int, Mapping[str, object]],
    slide_context: tuple[int, dict[int, str]],
) -> tuple[str, str] | None:
    """Resolve heading and note for one slide, preferring EN translations."""
    slide_index, outline_by_index = slide_context
    en: object = translations_en.get(slide_index)
    note = ""
    if isinstance(en, Mapping):
        en_note = en.get(LONG_FORM_NOTES_KEY)
        if isinstance(en_note, str) and en_note.strip():
            note = en_note.strip()
    if not note:
        note = _extract_long_form_note(slide)
    if not note:
        return None
    heading = _resolve_section_heading(slide, outline_by_index)
    if isinstance(en, Mapping):
        en_heading = en.get(OUTLINE_LEGACY_HEADING_KEY) or en.get("heading")
        if isinstance(en_heading, str) and en_heading.strip():
            heading = en_heading.strip()
    return heading, note


def build_blog_markdown_en_from_long_form_notes(
    composition: BlogCompositionInput,
    translations_en: Mapping[int, Mapping[str, object]],
) -> str:
    """Build EN blog markdown from translated long-form notes when available."""
    sections: list[str] = [f"# {composition.title}", ""]
    research = composition.research_summary.strip()
    if research:
        sections.append(research)
        sections.append("")

    outline_by_index = _outline_index(composition.outline)
    for index, slide in enumerate(composition.slides[:MAX_SLIDES]):
        if not isinstance(slide, dict):
            continue
        slide_index = _resolve_slide_index(slide, index + 1)
        resolved = _resolve_en_slide_content(
            slide, translations_en, (slide_index, outline_by_index)
        )
        if resolved is None:
            continue
        heading, note = resolved
        sections.append(f"{BLOG_SECTION_HEADING_PREFIX}{heading}")
        sections.append("")
        sections.append(note)
        sections.append("")

    return "\n".join(sections).strip()


__all__ = [
    "BlogCompositionInput",
    "build_blog_markdown_en_from_long_form_notes",
    "build_blog_markdown_from_long_form_notes",
]
