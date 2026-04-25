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
from typing import cast

from rag_backend.application.services.carousel.types import (
    MAX_FEATURE_ITEMS,
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
_ERR_JSON_NOT_FOUND = "No valid JSON object found"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

TITLE_TEMPERATURE = 0.8
CONTENT_TEMPERATURE = 0.7


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] — a common LLM JSON mistake."""
    # Remove commas followed immediately by } or ]
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _find_json_object(text: str) -> str | None:
    """Use brace counting to find the outermost JSON object in *text*."""
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return text[start : i + 1]
    return None


def extract_json(raw: str) -> object:
    """Parse JSON from an LLM response, tolerating markdown code fences,
    leading/trailing prose, trailing commas, and multiple code blocks.

    Raises json.JSONDecodeError only when every strategy fails.
    """
    candidate = raw.strip()

    # Strategy 1: raw string is valid JSON
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Strategy 2: try each markdown code block (non-greedy match may
    # catch the first block; we iterate all of them).
    for match in _JSON_FENCE_RE.finditer(candidate):
        block = match.group(1).strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass

    # Strategy 3: brace-counting to find the outermost {…} object
    obj_text = _find_json_object(candidate)
    if obj_text:
        try:
            return json.loads(obj_text)
        except json.JSONDecodeError:
            pass
        # Strategy 3b: same object with trailing commas stripped
        cleaned = _strip_trailing_commas(obj_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Strategy 4: naive first-{ to last-} with trailing-comma cleanup
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last != -1 and last > first:
        snippet = _strip_trailing_commas(candidate[first : last + 1])
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(_ERR_JSON_NOT_FOUND, raw, 0)


_JSON_REPAIR_PROMPT = (
    "Your previous response contained invalid JSON. "
    "Please return ONLY the corrected JSON object, with no additional text, "
    "no markdown fences, and no explanations."
)


async def _extract_json_with_repair(
    raw: str,
    *,
    llm: LLMService,
    project_id: str,
) -> dict[str, object]:
    """Parse JSON from an LLM response, with one LLM retry on failure.

    First tries the robust ``extract_json`` heuristics. If those fail,
    sends the raw response back to the LLM with a repair prompt and
    tries again. This handles cases where the LLM returns malformed
    JSON, comments, or explanatory text mixed with the payload.
    """
    try:
        return cast(dict[str, object], extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.warning(
            "carousel_content_json_parse_failed_attempt_1",
            project_id=project_id,
            error=str(exc),
            raw_response=raw[:2000],
        )

    repair_response = await llm.generate(
        messages=[
            {"role": "user", "content": raw},
            {"role": "assistant", "content": _JSON_REPAIR_PROMPT},
        ],
        temperature=0.2,
    )

    try:
        return cast(dict[str, object], extract_json(repair_response))
    except json.JSONDecodeError as exc:
        logger.exception(
            "carousel_content_json_parse_failed_attempt_2",
            project_id=project_id,
            error=str(exc),
            raw_response=raw[:2000],
            repair_response=repair_response[:2000],
        )
        raise


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


def _parse_slides(content_data: dict[str, object]) -> list[SlideData]:
    """Materialize the LLM's `slides` array into SlideData dataclasses.

    Raises ValueError if the shape is malformed; the caller turns that
    into a pipeline abort so we never persist half-parsed slides.
    """
    slides_data: list[SlideData] = []
    raw_slides = content_data.get("slides", [])
    if not isinstance(raw_slides, list):
        raw_slides = []
    for slide_json in raw_slides:
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

    blog_pt = str(content_data.get("blog_pt", content_data.get("blog_markdown", "")))
    blog_en = str(content_data.get("blog_en", ""))

    project.blog_markdown = blog_pt
    project.blog_translations = {"pt": blog_pt, "en": blog_en} if blog_en else {"pt": blog_pt}

    # Parse blog_image_map if present; defensively normalize to a list
    # of dicts with slide_number (int) and heading (str).
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

    # Store English title/subtitle when provided by the LLM
    if "title_en" in content_data:
        title_en_value = content_data.get("title_en")
        subtitle_en_value = content_data.get("subtitle_en")
        project.set_title_en(
            title=str(title_en_value) if title_en_value is not None else "",
            subtitle=str(subtitle_en_value) if subtitle_en_value is not None else None,
        )

    return slides_data, project.blog_markdown or ""
