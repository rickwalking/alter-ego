"""Caption and translation generation for editorial distribution."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

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
    _slide_long_form_notes,
)
from rag_backend.application.services.carousel.editorial_translation_structure import (
    structured_source,
    structured_translation,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_rubric import (
    RUBRIC_AUDIENCE_TRANSLATION,
    render_quality_rubric,
)
from rag_backend.application.services.carousel.types import MAX_SLIDES
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.carousel_template.prompts import (
    build_slide_translation_prompt,
)
from rag_backend.domain.constants.ai_agents import PROMPT_EDITORIAL_CAPTION_FALLBACK
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.copy_sanitize import sanitize_model_copy
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
            headings.append((index, sanitize_model_copy(title.strip())))
    return headings


async def _generate_caption(
    llm: BaseChatModel,
    project: CarouselProject,
    slide_drafts: list[dict[str, object]],
) -> str:
    headings = _slide_headings_for_caption(slide_drafts)
    safe_title = sanitize_model_copy(project.title or project.topic)
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
        # AE-0347: fall back to the 1-based position like every other resolver.
        index = int(slide.get(SLIDE_INDEX_KEY, len(payload) + 1))
        # AE-0366: case- and markup-preserving. The lowercasing sanitizer sent
        # "argon ... strongindirect prompt injections/strong" to the translator,
        # which came back as a fully lowercase EN slide with mangled tags.
        item: dict[str, object] = {
            SLIDE_INDEX_KEY: index,
            OUTLINE_LEGACY_HEADING_KEY: sanitize_model_copy(_slide_heading(slide)),
            OUTLINE_LEGACY_BODY_KEY: sanitize_model_copy(_slide_body(slide)),
        }
        # AE-0347: ship the PT long-form notes so the EN blog gets translated prose.
        # Sent verbatim: the notes are model output already inside our pipeline
        # (user inputs were sanitized at intake) and the lowercasing sanitizer
        # would come back as a lowercased EN blog.
        notes = _slide_long_form_notes(slide)
        if notes:
            item[LONG_FORM_NOTES_KEY] = notes
        # AE-0430: the TL;DR and item texts travel too, so EN keeps PT's shape.
        item.update(structured_source(slide))
        payload.append(item)
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
        translation.update(structured_source(item))
        result[index] = translation
    return result


def _with_pt_structure(
    translations: dict[int, dict[str, object]],
    slide_drafts: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    """AE-0430: every translated slide carries its PT draft's structured extras."""
    for position, slide in enumerate(slide_drafts[:MAX_SLIDES]):
        if not isinstance(slide, dict):
            continue
        index = int(slide.get(SLIDE_INDEX_KEY, position + 1))
        translation = translations.get(index)
        if translation is not None:
            translation.update(structured_translation(slide, translation))
    return translations


async def _generate_en_translations(
    llm: BaseChatModel,
    slide_drafts: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    payload = _build_translation_payload(slide_drafts)
    if not payload:
        return {}
    # AE-0366: versioned YAML prompt carrying the contract's quality rubric.
    prompt = build_slide_translation_prompt(
        json.dumps(payload, ensure_ascii=False),
        render_quality_rubric(
            load_presentation_policy(CREATE_TIME_PRESENTATION_POLICY_VERSION),
            RUBRIC_AUDIENCE_TRANSLATION,
        ),
    )
    response = await llm.ainvoke(
        [HumanMessage(content=prompt)],
        get_langfuse_runnable_config(),
    )
    try:
        data = cast(dict[str, object], extract_json(str(response.content)))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(ERR_EN_TRANSLATION_PARSE_FAILED) from exc
    return _with_pt_structure(_parse_translation_response(data), slide_drafts)


__all__ = [
    "_generate_caption",
    "_generate_en_translations",
]
