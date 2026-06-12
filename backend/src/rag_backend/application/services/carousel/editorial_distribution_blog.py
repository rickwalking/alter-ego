"""Blog composition helpers for editorial distribution."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.carousel.blog_composition import (
    BlogCompositionInput,
    build_blog_markdown_en_from_long_form_notes,
    build_blog_markdown_from_long_form_notes,
)

ERR_TRANSLATIONS_REQUIRED = "translations_en required for EN build"


@dataclass
class BlogBuildContext:
    """Bundled parameters for blog markdown construction."""

    slide_drafts: list[dict[str, object]]
    title: str
    research_summary: str = ""
    outline: list[dict[str, object]] | None = None
    translations_en: dict[int, dict[str, object]] | None = None


def build_blog_markdown_en_from_translations(ctx: BlogBuildContext) -> str:
    """Build English blog markdown from EN long-form notes."""
    if ctx.translations_en is None:
        raise ValueError(ERR_TRANSLATIONS_REQUIRED)
    return build_blog_markdown_en_from_long_form_notes(
        BlogCompositionInput(
            slides=tuple(
                slide for slide in ctx.slide_drafts if isinstance(slide, dict)
            ),
            title=ctx.title,
            research_summary=ctx.research_summary,
            outline=tuple(item for item in ctx.outline or [] if isinstance(item, dict)),
        ),
        ctx.translations_en,
    )


def build_blog_markdown_from_drafts(ctx: BlogBuildContext) -> str:
    """Build public blog markdown from long-form notes instead of slide bodies."""
    return build_blog_markdown_from_long_form_notes(
        BlogCompositionInput(
            slides=tuple(
                slide for slide in ctx.slide_drafts if isinstance(slide, dict)
            ),
            title=ctx.title,
            research_summary=ctx.research_summary,
            outline=tuple(item for item in ctx.outline or [] if isinstance(item, dict)),
        ),
    )


__all__ = [
    "BlogBuildContext",
    "build_blog_markdown_en_from_translations",
    "build_blog_markdown_from_drafts",
]
