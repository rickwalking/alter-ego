"""Caption and translation generation for editorial distribution."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    CAPTION_FALLBACK_HEADINGS_PLACEHOLDER,
    ERR_EN_TRANSLATION_PARSE_FAILED,
    JSON_SLIDE_NUMBER_ALIAS_KEY,
    JSON_SLIDES_EN_KEY,
    LONG_FORM_NOTES_KEY,
    OUTLINE_LEGACY_BODY_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.editorial_distribution_slide import (
    _slide_body,
    _slide_heading,
)
from rag_backend.application.services.carousel.types import MAX_SLIDES
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.constants.ai_agents import (
    PROMPT_EDITORIAL_CAPTION_FALLBACK,
    PROMPT_EDITORIAL_SLIDE_TRANSLATIONS,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config


def _slide_headings_for_caption(
    slide_drafts: list[dict[str, object]],
) -> list[tuple[int, str]]:
    from rag_backend.application.services.carousel.editorial_distribution_constants import (
        DEFAULT_UNTITLED_SLIDE_LABEL,
    )

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


def _build_translation_payload(
    slide_drafts: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build the list of slides to send for EN translation."""
    payload: list[dict[str, object]] = []
    for slide in slide_drafts[:MAX_SLIDES]:
        if not isinstance(slide, dict):
            continue
        index = int(slide.get(SLIDE_INDEX_KEY, 0))
        payload.append({
            SLIDE_INDEX_KEY: index,
            OUTLINE_LEGACY_HEADING_KEY: sanitize_llm_input(_slide_heading(slide)),
            OUTLINE_LEGACY_BODY_KEY: sanitize_llm_input(_slide_body(slide)),
        })
    return payload


def _parse_translation_response(
    data: dict[str, object],
) -> dict[int, dict[str, object]]:
    """Parse the LLM translation response into indexed translations."""
    raw_en = data.get(JSON_SLIDES_EN_KEY, [])
    if not isinstance(raw_en, list):
        raise TypeError(ERR_EN_TRANSLATION_PARSE_FAILED)
    result: dict[int, dict[str, object]] = {}
    for item in raw_en:
        if not isinstance(item, dict):
            continue
        index = item.get(SLIDE_INDEX_KEY, item.get(JSON_SLIDE_NUMBER_ALIAS_KEY))
        if not isinstance(index, int):
            continue
        translation: dict[str, object] = {
            OUTLINE_LEGACY_HEADING_KEY: str(item.get(OUTLINE_LEGACY_HEADING_KEY, "")),
            OUTLINE_LEGACY_BODY_KEY: str(item.get(OUTLINE_LEGACY_BODY_KEY, "")),
        }
        en_notes = item.get(LONG_FORM_NOTES_KEY)
        if isinstance(en_notes, str) and en_notes.strip():
            translation[LONG_FORM_NOTES_KEY] = en_notes.strip()
        result[index] = translation
    return result


async def _generate_en_translations(
    llm: BaseChatModel,
    slide_drafts: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    payload = _build_translation_payload(slide_drafts)
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
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(ERR_EN_TRANSLATION_PARSE_FAILED) from exc
    return _parse_translation_response(data)


__all__ = [
    "_generate_caption",
    "_generate_en_translations",
]
