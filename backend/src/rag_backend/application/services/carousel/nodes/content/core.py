"""Phases 2-3: title optimization + bilingual content synthesis.

Issues two LLM calls:
1. Title prompt — picks a hookier PT/EN title pair
2. Content prompt — returns bilingual slides + blog markdown as JSON

Both payloads are parsed defensively: JSON often arrives wrapped in
markdown code fences, and ``slides_en`` may be absent for LLMs that skip
the translation pass.
"""

from __future__ import annotations

import json
from typing import cast

from rag_backend.application.services.carousel.nodes.content.blog_cleanup import (
    cleanup_blog_markdown,
)
from rag_backend.application.services.carousel.nodes.content.json_utils import (
    _extract_json_with_repair,
    extract_json,
)
from rag_backend.application.services.carousel.nodes.content.slides import _parse_slides
from rag_backend.application.services.carousel.types import (
    MAX_SLIDES,
    SlideData,
    build_slides_en_index,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.models import CarouselProject, ResearchSource
from rag_backend.domain.protocols import LLMService
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_ERR_CONTENT_NON_JSON = "Content synthesis returned non-JSON output; cannot continue."
_ERR_CONTENT_INVALID_SLIDES = "Content synthesis returned slides with missing fields."
_ERR_CONTENT_ZERO_SLIDES = "Content synthesis returned zero slides."

TITLE_TEMPERATURE = 0.8
CONTENT_TEMPERATURE = 0.7


async def _optimize_title(
    project: CarouselProject,
    research_context: str,
    *,
    llm: LLMService,
    template: CarouselTemplateBuilder,
) -> None:
    title_prompt = template.build_title_prompt(project, research_context)
    title_response = await llm.generate(
        messages=[{"role": "user", "content": title_prompt}],
        temperature=TITLE_TEMPERATURE,
    )

    try:
        title_data = cast(dict[str, object], extract_json(title_response))
        subtitle_value = title_data.get("subtitle_pt", title_data.get("subtitle"))
        project.set_title(
            title=str(title_data.get("title_pt", title_data.get("title", project.topic))),
            subtitle=str(subtitle_value) if subtitle_value is not None else None,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning(
            "carousel_title_json_parse_failed",
            project_id=str(project.id),
            error=str(exc),
            raw_response=title_response[:2000],
        )
        project.set_title(title=project.topic)


async def run_content(
    project: CarouselProject,
    sources: list[ResearchSource],
    *,
    llm: LLMService,
    template: CarouselTemplateBuilder,
) -> tuple[list[SlideData], str]:
    research_context = "\n\n".join(
        f"Source: {s.source_url}\n{s.extracted_content or ''}"
        for s in sources
        if s.extracted_content
    )

    await _optimize_title(project, research_context, llm=llm, template=template)

    content_prompt = template.build_content_prompt(project, research_context)
    content_response = await llm.generate(
        messages=[{"role": "user", "content": content_prompt}],
        temperature=CONTENT_TEMPERATURE,
    )

    try:
        content_data = await _extract_json_with_repair(
            content_response,
            llm=llm,
            project_id=str(project.id),
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(_ERR_CONTENT_NON_JSON) from exc

    try:
        slides_data = _parse_slides(content_data)
        slides_en_by_number = build_slides_en_index(content_data.get("slides_en"))
        for sd in slides_data:
            en = slides_en_by_number.get(sd.slide_number)
            if en is not None:
                sd.translation_en = en
    except (KeyError, TypeError) as exc:
        logger.exception(
            "carousel_slide_shape_invalid",
            project_id=str(project.id),
            error=str(exc),
            content_keys=list(content_data.keys()) if isinstance(content_data, dict) else None,
        )
        raise ValueError(_ERR_CONTENT_INVALID_SLIDES) from exc

    if not slides_data:
        logger.error(
            "carousel_no_slides_produced",
            project_id=str(project.id),
            content_keys=list(content_data.keys()),
        )
        raise ValueError(_ERR_CONTENT_ZERO_SLIDES)

    blog_pt_raw = str(content_data.get("blog_pt", content_data.get("blog_markdown", "")))
    blog_en_raw = str(content_data.get("blog_en", ""))

    blog_pt = cleanup_blog_markdown(blog_pt_raw)
    blog_en = cleanup_blog_markdown(blog_en_raw) if blog_en_raw else ""

    project.blog_markdown = blog_pt
    project.blog_translations = {"pt": blog_pt, "en": blog_en} if blog_en else {"pt": blog_pt}

    raw_image_map = content_data.get("blog_image_map")
    if isinstance(raw_image_map, list):
        image_map: list[dict[str, str | int]] = []
        for entry in raw_image_map:
            if isinstance(entry, dict):
                slide_number = entry.get("slide_number")
                heading = entry.get("heading")
                if isinstance(slide_number, int) and 1 <= slide_number <= MAX_SLIDES:
                    image_map.append(
                        {
                            "slide_number": slide_number,
                            "heading": str(heading) if heading is not None else "",
                            "alt": str(entry.get("alt", "")),
                        }
                    )
        project.blog_image_map = image_map if image_map else None

    if "title_pt" in content_data:
        title_value = content_data.get("title_pt", project.title or project.topic)
        subtitle_value = content_data.get("subtitle_pt", project.subtitle)
        project.set_title(
            title=str(title_value) if title_value is not None else project.topic,
            subtitle=str(subtitle_value) if subtitle_value is not None else None,
        )

    if "title_en" in content_data:
        title_en_value = content_data.get("title_en")
        subtitle_en_value = content_data.get("subtitle_en")
        project.set_title_en(
            title=str(title_en_value) if title_en_value is not None else "",
            subtitle=str(subtitle_en_value) if subtitle_en_value is not None else None,
        )

    return slides_data, project.blog_markdown or ""
