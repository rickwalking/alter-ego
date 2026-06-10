"""Blog composition helpers for editorial distribution."""

from __future__ import annotations

from rag_backend.application.services.carousel.blog_composition import (
    BlogCompositionInput,
    build_blog_markdown_en_from_long_form_notes,
    build_blog_markdown_from_long_form_notes,
)


def build_blog_markdown_en_from_translations(
    slide_drafts: list[dict[str, object]],
    translations_en: dict[int, dict[str, object]],
    *,
    title: str,
    research_summary: str = "",
    outline: list[dict[str, object]] | None = None,
) -> str:
    """Build English blog markdown from EN long-form notes."""
    return build_blog_markdown_en_from_long_form_notes(
        BlogCompositionInput(
            slides=tuple(slide for slide in slide_drafts if isinstance(slide, dict)),
            title=title,
            research_summary=research_summary,
            outline=tuple(item for item in outline or [] if isinstance(item, dict)),
        ),
        translations_en,
    )


def build_blog_markdown_from_drafts(
    slide_drafts: list[dict[str, object]],
    *,
    title: str,
    research_summary: str = "",
    outline: list[dict[str, object]] | None = None,
) -> str:
    """Build public blog markdown from long-form notes instead of slide bodies."""
    return build_blog_markdown_from_long_form_notes(
        BlogCompositionInput(
            slides=tuple(slide for slide in slide_drafts if isinstance(slide, dict)),
            title=title,
            research_summary=research_summary,
            outline=tuple(item for item in outline or [] if isinstance(item, dict)),
        ),
    )


__all__ = [
    "build_blog_markdown_en_from_translations",
    "build_blog_markdown_from_drafts",
]
