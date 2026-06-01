"""Persist captions, blog, LinkedIn copy, and EN translations for editorial workflows."""

from __future__ import annotations

import json
from typing import cast
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    BLOG_LANG_ENGLISH,
    BLOG_LANG_PORTUGUESE,
    CAPTION_FALLBACK_HEADINGS_PLACEHOLDER,
    DEFAULT_UNTITLED_SLIDE_LABEL,
    JSON_SLIDE_NUMBER_ALIAS_KEY,
    JSON_SLIDES_EN_KEY,
    OUTLINE_FIELD_SLIDE_TYPE,
    OUTLINE_LEGACY_BODY_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
    SLIDE_DRAFT_TEXT_KEY,
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_SLIDE_INDEX,
    OUTLINE_FIELD_TITLE,
    canonical_slide_type,
)
from rag_backend.application.services.carousel.types import (
    MAX_SLIDES,
    SlideData,
    pack_extras,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.linkedin_post_generator import (
    LinkedInPostGenerator,
)
from rag_backend.domain.constants.ai_agents import (
    PROMPT_EDITORIAL_CAPTION_FALLBACK,
    PROMPT_EDITORIAL_SLIDE_TRANSLATIONS,
)
from rag_backend.domain.constants.carousel import CAROUSEL_SLIDES_CONFIG_SEVEN
from rag_backend.domain.constants.carousel_workflow import (
    WORKFLOW_STATE_LINKEDIN_POST_EN_KEY,
    WORKFLOW_STATE_LINKEDIN_POST_PT_KEY,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config

BLOG_SECTION_HEADING_PREFIX = "## "


def _slide_heading(slide: dict[str, object]) -> str:
    return str(
        slide.get(OUTLINE_FIELD_TITLE, "")
        or slide.get(OUTLINE_LEGACY_HEADING_KEY, "")
        or DEFAULT_UNTITLED_SLIDE_LABEL
    )


def _slide_body(slide: dict[str, object]) -> str:
    return str(
        slide.get(SLIDE_DRAFT_TEXT_KEY, "") or slide.get(OUTLINE_LEGACY_BODY_KEY, "")
    )


def build_blog_markdown_en_from_translations(
    slide_drafts: list[dict[str, object]],
    translations_en: dict[int, dict[str, object]],
    *,
    title: str,
) -> str:
    """Build English blog markdown from EN slide translations."""
    sections: list[str] = [f"# {title}", ""]
    for slide in slide_drafts[:MAX_SLIDES]:
        if not isinstance(slide, dict):
            continue
        index = int(slide.get(SLIDE_INDEX_KEY, 0))
        en = translations_en.get(index, {})
        heading = str(en.get(OUTLINE_LEGACY_HEADING_KEY, "")) or _slide_heading(slide)
        body = str(en.get(OUTLINE_LEGACY_BODY_KEY, "")) or _slide_body(slide)
        if not body.strip():
            continue
        sections.append(f"{BLOG_SECTION_HEADING_PREFIX}{heading}")
        sections.append("")
        sections.append(body.strip())
        sections.append("")
    return "\n".join(sections).strip()


def build_blog_markdown_from_drafts(
    slide_drafts: list[dict[str, object]],
    *,
    title: str,
) -> str:
    """Build a minimal public blog post from persisted slide drafts."""
    sections: list[str] = [f"# {title}", ""]
    for slide in slide_drafts[:MAX_SLIDES]:
        if not isinstance(slide, dict):
            continue
        heading = _slide_heading(slide)
        body = _slide_body(slide)
        if not body.strip():
            continue
        sections.append(f"{BLOG_SECTION_HEADING_PREFIX}{heading}")
        sections.append("")
        sections.append(body.strip())
        sections.append("")
    return "\n".join(sections).strip()


def _slide_headings_for_caption(
    slide_drafts: list[dict[str, object]],
) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for slide in slide_drafts[:MAX_SLIDES]:
        if not isinstance(slide, dict):
            continue
        index = int(slide.get(SLIDE_INDEX_KEY, len(headings) + 1))
        title = _slide_heading(slide)
        if title.strip() and title != DEFAULT_UNTITLED_SLIDE_LABEL:
            headings.append((index, sanitize_llm_input(title.strip())))
    return headings


async def _generate_caption(
    llm: BaseChatModel,
    project: CarouselProject,
    slide_drafts: list[dict[str, object]],
) -> str:
    headings = _slide_headings_for_caption(slide_drafts)
    safe_title = sanitize_llm_input(project.title or project.topic)
    template = CarouselTemplateBuilder()
    if headings:
        prompt = template.build_caption_prompt(project, headings)
    else:
        prompt = PROMPT_EDITORIAL_CAPTION_FALLBACK.format(
            title=safe_title,
            headings=CAPTION_FALLBACK_HEADINGS_PLACEHOLDER,
        )
    response = await llm.ainvoke(
        [HumanMessage(content=prompt)],
        get_langfuse_runnable_config(),
    )
    return str(response.content).strip()


async def _generate_en_translations(
    llm: BaseChatModel,
    slide_drafts: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    payload = []
    for slide in slide_drafts[:MAX_SLIDES]:
        if not isinstance(slide, dict):
            continue
        index = int(slide.get(SLIDE_INDEX_KEY, 0))
        payload.append({
            SLIDE_INDEX_KEY: index,
            OUTLINE_LEGACY_HEADING_KEY: sanitize_llm_input(_slide_heading(slide)),
            OUTLINE_LEGACY_BODY_KEY: sanitize_llm_input(_slide_body(slide)),
        })
    if not payload:
        return {}
    prompt = PROMPT_EDITORIAL_SLIDE_TRANSLATIONS.format(
        slides_json=json.dumps(payload, ensure_ascii=False),
    )
    response = await llm.ainvoke(
        [HumanMessage(content=prompt)],
        get_langfuse_runnable_config(),
    )
    try:
        data = cast(dict[str, object], extract_json(str(response.content)))
    except (json.JSONDecodeError, TypeError):
        return {}
    raw_en = data.get(JSON_SLIDES_EN_KEY, [])
    if not isinstance(raw_en, list):
        return {}
    result: dict[int, dict[str, object]] = {}
    for item in raw_en:
        if not isinstance(item, dict):
            continue
        index = item.get(SLIDE_INDEX_KEY, item.get(JSON_SLIDE_NUMBER_ALIAS_KEY))
        if not isinstance(index, int):
            continue
        result[index] = {
            OUTLINE_LEGACY_HEADING_KEY: str(item.get(OUTLINE_LEGACY_HEADING_KEY, "")),
            OUTLINE_LEGACY_BODY_KEY: str(item.get(OUTLINE_LEGACY_BODY_KEY, "")),
        }
    return result


async def apply_slide_drafts_to_database(
    db: AsyncSession,
    project_id: str,
    outline: list[dict[str, object]],
    slide_drafts: list[dict[str, object]],
    translations_en: dict[int, dict[str, object]],
) -> None:
    """Merge outline + drafts (+ EN) into persisted carousel slides."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None:
        return

    drafts_by_index: dict[int, dict[str, object]] = {}
    for draft in slide_drafts:
        if isinstance(draft, dict):
            drafts_by_index[int(draft.get(SLIDE_INDEX_KEY, 0))] = draft

    existing = await repo.get_slides_by_project(project.id)
    if existing:
        for slide in existing:
            draft = drafts_by_index.get(slide.slide_number)
            if draft is None:
                continue
            slide.heading = _slide_heading(draft)
            slide.body = _slide_body(draft)
            en = translations_en.get(slide.slide_number)
            if en:
                slide_data = SlideData(
                    slide_number=slide.slide_number,
                    slide_type=slide.slide_type,
                    heading=slide.heading,
                    body=slide.body,
                    translation_en=en,
                )
                slide.extras = pack_extras(slide_data)
            await repo.update_slide(slide)
        project.slides_config = CAROUSEL_SLIDES_CONFIG_SEVEN
        await repo.update_project(project)
        return

    for index, item in enumerate(outline[:MAX_SLIDES]):
        if not isinstance(item, dict):
            continue
        slide_number = int(item.get(OUTLINE_FIELD_SLIDE_INDEX, index + 1))
        draft = drafts_by_index.get(slide_number, item)
        heading = _slide_heading(draft)
        body = _slide_body(draft)
        slide_type = str(
            item.get(OUTLINE_FIELD_SLIDE_TYPE, "") or canonical_slide_type(slide_number)
        )
        en = translations_en.get(slide_number)
        slide_data = SlideData(
            slide_number=slide_number,
            slide_type=slide_type,
            heading=heading,
            body=body,
            translation_en=en,
        )
        await repo.create_slide(
            CarouselSlide(
                project_id=project.id,
                slide_number=slide_number,
                slide_type=slide_type,
                heading=heading,
                body=body,
                extras=pack_extras(slide_data),
            )
        )
    project.slides_config = CAROUSEL_SLIDES_CONFIG_SEVEN
    await repo.update_project(project)


async def build_editorial_distribution_updates(
    db: AsyncSession,
    llm: BaseChatModel,
    project_id: str,
    outline: list[dict[str, object]],
    slide_drafts: list[dict[str, object]],
    *,
    linkedin_generator: LinkedInPostGenerator | None = None,
) -> dict[str, object]:
    """Generate and persist distribution fields; return workflow state updates."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None or not slide_drafts:
        return {}

    translations_en = await _generate_en_translations(llm, slide_drafts)
    await apply_slide_drafts_to_database(
        db,
        project_id,
        outline,
        slide_drafts,
        translations_en,
    )

    project = await repo.get_project_by_id(UUID(project_id))
    if project is None:
        return {}

    blog_pt = build_blog_markdown_from_drafts(
        slide_drafts,
        title=project.title or project.topic,
    )
    blog_en = build_blog_markdown_en_from_translations(
        slide_drafts,
        translations_en,
        title=project.title_en or project.title or project.topic,
    )
    project.blog_markdown = blog_pt
    project.blog_translations = {
        BLOG_LANG_PORTUGUESE: blog_pt,
        BLOG_LANG_ENGLISH: blog_en or blog_pt,
    }

    caption = await _generate_caption(llm, project, slide_drafts)
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
    }


__all__ = [
    "apply_slide_drafts_to_database",
    "build_blog_markdown_en_from_translations",
    "build_blog_markdown_from_drafts",
    "build_editorial_distribution_updates",
]
