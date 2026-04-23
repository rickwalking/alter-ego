"""Phases 2-3: title optimization + bilingual content synthesis.

Issues two LLM calls:
1. Title prompt — picks a hookier PT/EN title pair
2. Content prompt — returns bilingual slides + blog markdown as JSON

Both payloads are parsed defensively: JSON often arrives wrapped in
markdown code fences, and `slides_en` may be absent for LLMs that skip
the translation pass.
"""

from __future__ import annotations

import json
import re
from typing import Any

from rag_backend.application.services.carousel.types import (
    MAX_FEATURE_ITEMS,
    SlideData,
    build_slides_en_index,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.models import CarouselProject, ResearchSource
from rag_backend.domain.protocols import LLMService
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

TITLE_TEMPERATURE = 0.8
CONTENT_TEMPERATURE = 0.7


def extract_json(raw: str) -> Any:
    """Parse JSON from an LLM response, tolerating markdown code fences
    and leading/trailing prose. Raises json.JSONDecodeError on failure.
    """
    candidate = raw.strip()
    fence_match = _JSON_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()
    else:
        first = candidate.find("{")
        last = candidate.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = candidate[first : last + 1]
    return json.loads(candidate)


async def _optimize_title(
    project: CarouselProject,
    research_context: str,
    *,
    llm: LLMService,
    template: CarouselTemplateBuilder,
) -> None:
    """Phase 2: pick a hookier title/subtitle. Mutates `project` in place."""
    title_prompt = template.build_title_prompt(project, research_context)
    title_response = await llm.generate(
        messages=[{"role": "user", "content": title_prompt}],
        temperature=TITLE_TEMPERATURE,
    )

    try:
        title_data = extract_json(title_response)
        project.set_title(
            title=title_data.get("title_pt", title_data.get("title", project.topic)),
            subtitle=title_data.get("subtitle_pt", title_data.get("subtitle")),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning(
            "carousel_title_json_parse_failed",
            project_id=str(project.id),
            error=str(exc),
            raw_response=title_response[:2000],
        )
        project.set_title(title=project.topic)


def _parse_slides(content_data: dict[str, Any]) -> list[SlideData]:
    """Materialize the LLM's `slides` array into SlideData dataclasses.

    Raises ValueError if the shape is malformed; the caller turns that
    into a pipeline abort so we never persist half-parsed slides.
    """
    slides_data: list[SlideData] = []
    for slide_json in content_data.get("slides", []):
        raw_features = slide_json.get("features")
        features: list[dict[str, str]] | None = None
        if isinstance(raw_features, list) and raw_features:
            # Defensive cap: the template's .feature-grid overflows past
            # 4 items. Even if the LLM ignores the prompt cap, truncate
            # here so the rendered JPG never overflows.
            features = [
                {
                    "icon": str(item.get("icon") or "✅"),
                    "title": str(item.get("title") or ""),
                    "body": str(item.get("body") or ""),
                }
                for item in raw_features[:MAX_FEATURE_ITEMS]
                if isinstance(item, dict)
            ]
        raw_stats = slide_json.get("stats")
        stats: list[dict[str, str]] | None = None
        if isinstance(raw_stats, list) and raw_stats:
            stats = [
                {
                    "value": str(item.get("value") or ""),
                    "label": str(item.get("label") or ""),
                    "detail": str(item.get("detail") or ""),
                }
                for item in raw_stats
                if isinstance(item, dict)
            ]
        raw_insight = slide_json.get("insight")
        insight: dict[str, str] | None = None
        if isinstance(raw_insight, dict) and raw_insight.get("quote"):
            insight = {
                "quote": str(raw_insight.get("quote") or ""),
                "attribution": str(raw_insight.get("attribution") or ""),
            }
        slides_data.append(
            SlideData(
                slide_number=slide_json["number"],
                slide_type=slide_json["type"],
                heading=slide_json["heading"],
                body=slide_json["body"],
                image_prompt=slide_json.get("image_prompt"),
                features=features,
                stats=stats,
                insight=insight,
            )
        )
    return slides_data


async def run_content(
    project: CarouselProject,
    sources: list[ResearchSource],
    *,
    llm: LLMService,
    template: CarouselTemplateBuilder,
) -> tuple[list[SlideData], str]:
    """Phases 2-3: optimize the title, then synthesize bilingual slides."""
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
        content_data = extract_json(content_response)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error(
            "carousel_content_json_parse_failed",
            project_id=str(project.id),
            error=str(exc),
            raw_response=content_response[:4000],
        )
        raise ValueError(
            "Content synthesis returned non-JSON output; cannot continue."
        ) from exc

    try:
        slides_data = _parse_slides(content_data)
        slides_en_by_number = build_slides_en_index(content_data.get("slides_en"))
        for sd in slides_data:
            en = slides_en_by_number.get(sd.slide_number)
            if en is not None:
                sd.translation_en = en
    except (KeyError, TypeError) as exc:
        logger.error(
            "carousel_slide_shape_invalid",
            project_id=str(project.id),
            error=str(exc),
            content_keys=list(content_data.keys()) if isinstance(content_data, dict) else None,
        )
        raise ValueError("Content synthesis returned slides with missing fields.") from exc

    if not slides_data:
        logger.error(
            "carousel_no_slides_produced",
            project_id=str(project.id),
            content_keys=list(content_data.keys()),
        )
        raise ValueError("Content synthesis returned zero slides.")

    blog_pt = content_data.get("blog_pt", content_data.get("blog_markdown", ""))
    blog_en = content_data.get("blog_en", "")

    project.blog_markdown = blog_pt
    project.blog_translations = {"pt": blog_pt, "en": blog_en} if blog_en else {"pt": blog_pt}

    if "title_pt" in content_data:
        project.set_title(
            title=content_data.get("title_pt", project.title or project.topic),
            subtitle=content_data.get("subtitle_pt", project.subtitle),
        )

    return slides_data, project.blog_markdown or ""
