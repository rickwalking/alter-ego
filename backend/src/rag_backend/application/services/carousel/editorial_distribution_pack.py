"""Orchestrate editorial distribution: captions, blog, LinkedIn, EN translations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.blog_composition import (
    _resolve_slide_index,
)
from rag_backend.application.services.carousel.editorial_distribution_blog import (
    BlogBuildContext,
    build_blog_markdown_en_from_translations,
    build_blog_markdown_from_drafts,
)
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    BLOG_LANG_ENGLISH,
    BLOG_LANG_PORTUGUESE,
    DEFAULT_UNTITLED_SLIDE_LABEL,
    OUTLINE_LEGACY_HEADING_KEY,
)
from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _generate_caption,
    _generate_en_translations,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    SlideDraftsContext as _SlideDraftsContext,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    apply_slide_drafts_to_database,
)
from rag_backend.application.services.carousel.editorial_distribution_slide import (
    _slide_heading,
)
from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_TRANSLATIONS_EN_KEY,
    serialize_translations_en,
)
from rag_backend.application.services.linkedin_post_generator import (
    LinkedInPostGenerator,
)
from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_STATE_LINKEDIN_POST_EN_KEY,
    WORKFLOW_STATE_LINKEDIN_POST_PT_KEY,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)


@dataclass(frozen=True)
class DistributionBuildContext:
    """Input bundle for building editorial distribution updates."""

    db: AsyncSession
    llm: BaseChatModel
    project_id: str
    outline: list[dict[str, object]]
    slide_drafts: list[dict[str, object]]
    research_summary: str = ""


def _ensure_blog_titles(
    project: CarouselProject,
    slide_drafts: list[dict[str, object]],
    translations_en: dict[int, dict[str, object]],
) -> None:
    """AE-0347: derive PT/EN titles from the intro slide when none are set.

    The editorial path never called ``set_title``/``set_title_en``, so the blog H1
    fell back to the raw (often English) ``topic`` in BOTH languages. Never
    overwrite a title the user or a prior run already set.
    """
    intro = next((s for s in slide_drafts if isinstance(s, dict)), None)
    if intro is None:
        return
    if not project.title:
        heading = _slide_heading(intro)
        if heading and heading != DEFAULT_UNTITLED_SLIDE_LABEL:
            project.set_title(heading)
    if not project.title_en:
        en = translations_en.get(_resolve_slide_index(intro, 1), {})
        en_heading = str(en.get(OUTLINE_LEGACY_HEADING_KEY) or "").strip()
        if en_heading:
            project.set_title_en(en_heading)


async def build_editorial_distribution_updates(
    context: DistributionBuildContext,
    *,
    linkedin_generator: LinkedInPostGenerator | None = None,
) -> dict[str, object]:
    """Generate and persist distribution fields; return workflow state updates."""
    repo = PostgresCarouselRepository(session=context.db)
    project = await repo.get_project_by_id(UUID(context.project_id))
    if project is None or not context.slide_drafts:
        return {}

    translations_en = await _generate_en_translations(context.llm, context.slide_drafts)
    await apply_slide_drafts_to_database(
        SlideDraftsContext(
            db=context.db,
            project_id=context.project_id,
            outline=context.outline,
            slide_drafts=context.slide_drafts,
            translations_en=translations_en,
        ),
    )

    project = await repo.get_project_by_id(UUID(context.project_id))
    if project is None:
        return {}

    _ensure_blog_titles(project, context.slide_drafts, translations_en)
    blog_title = project.title or project.topic
    blog_en_title = project.title_en or blog_title
    composition_kwargs = {
        "research_summary": context.research_summary,
        "outline": context.outline,
    }
    blog_pt = build_blog_markdown_from_drafts(
        BlogBuildContext(
            slide_drafts=context.slide_drafts,
            title=blog_title,
            **composition_kwargs,
        ),
    )
    blog_en = build_blog_markdown_en_from_translations(
        BlogBuildContext(
            slide_drafts=context.slide_drafts,
            translations_en=translations_en,
            title=blog_en_title,
            **composition_kwargs,
        ),
    )
    project.blog_markdown = blog_pt
    project.blog_translations = {
        BLOG_LANG_PORTUGUESE: blog_pt,
        BLOG_LANG_ENGLISH: blog_en or blog_pt,
    }

    caption = await _generate_caption(context.llm, project, context.slide_drafts)
    project.caption = caption

    if linkedin_generator is not None and blog_pt.strip():
        post_pt, post_en = await linkedin_generator.generate_both(project)
        if post_pt is not None:
            project.linkedin_post_pt = post_pt.text
        if post_en is not None:
            project.linkedin_post_en = post_en.text

    await repo.update_project(project)

    return {
        "caption": project.caption or "",
        "blog_markdown": project.blog_markdown or "",
        WORKFLOW_STATE_LINKEDIN_POST_PT_KEY: project.linkedin_post_pt or "",
        WORKFLOW_STATE_LINKEDIN_POST_EN_KEY: project.linkedin_post_en or "",
        WORKFLOW_STATE_TRANSLATIONS_EN_KEY: serialize_translations_en(translations_en),
        "translations_en": translations_en,
    }


# Backward-compatible re-export
SlideDraftsContext = _SlideDraftsContext


__all__ = [
    "DistributionBuildContext",
    "SlideDraftsContext",
    "apply_slide_drafts_to_database",
    "build_blog_markdown_en_from_translations",
    "build_blog_markdown_from_drafts",
    "build_editorial_distribution_updates",
]
