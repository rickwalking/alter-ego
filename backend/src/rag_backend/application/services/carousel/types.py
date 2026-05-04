"""Shared types + helpers for the carousel pipeline.

Lifted from carousel_agent.py during the LangGraph refactor so nodes and
the legacy `CarouselAgent` class can share the same data shapes without
circular imports. Pure-data / pure-function module — no side effects,
no repository or LLM dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from rag_backend.domain.models import CarouselSlide

# Hard cap on closing/content slide feature cards. The .feature-grid CSS
# is tuned for 2-4 items; 5+ overflow past the slide footer.
MAX_FEATURE_ITEMS = 4

# Maximum number of slides in a carousel (includes intro, summary, content,
# closing, and CTA).
MAX_SLIDES = 7

# Fields copied from SlideData into the persisted `extras` JSON. Listed
# here so `pack_extras` stays a one-liner loop instead of four branches.
EXTRAS_FIELDS: tuple[str, ...] = (
    "features",
    "stats",
    "insight",
    "image_prompt",
    "translation_en",
    "summary_points",
    "tldr_strip",
)

# (image_model, image_style) → human-readable preset name, surfaced in
# the phase-progress label during image gen.
IMAGE_PRESET_DISPLAY: dict[tuple[str, str], str] = {
    ("gemini", "comic_neon"): "Gemini Comic Neon",
    ("openai", "cinematic"): "OpenAI Cinematic Photoreal",
    ("openai", "hyperreal"): "OpenAI Hyperreal Graphic Novel",
    ("openai", "neo_anime"): "OpenAI Neo-Anime",
}


class SlideDict(TypedDict, total=False):
    """Dictionary shape passed to template renderers."""

    number: int | str
    type: str
    heading: str
    body: str
    features: list[dict[str, str]] | None
    stats: list[dict[str, str]] | None
    insight: dict[str, str] | None
    image_prompt: str | None
    summary_points: list[dict[str, str]] | None
    tldr_strip: str | None


@dataclass
class SlideData:
    """Structured slide data from content synthesis."""

    slide_number: int
    slide_type: str
    heading: str
    body: str
    image_prompt: str | None = None
    # Structured checklist items for closing/feature slides. Each item is
    # `{"icon": "📝", "title": "...", "body": "..."}`. None for plain-prose
    # slides (intro, CTA, most content slides).
    features: list[dict[str, str]] | None = None
    # Big-number stat cards rendered as a 3-column grid. Each item is
    # `{"value": "80.2%", "label": "SWE-Bench Verified", "detail": "(era 68.9%)"}`.
    stats: list[dict[str, str]] | None = None
    # A single quoted insight with attribution rendered as an accent-
    # bordered card. Shape: `{"quote": "...", "attribution": "..."}`.
    insight: dict[str, str] | None = None
    # Parallel EN counterpart to (heading, body, features, stats, insight)
    # for bilingual rendering. None = no translation provided; we fall
    # back to PT when rendering EN slides.
    translation_en: dict[str, object] | None = None
    # Three snapshot cards for the summary slide (slide 2). Each item is
    # `{"icon": "🎯", "title": "...", "body": "..."}`. None for non-summary slides.
    summary_points: list[dict[str, str]] | None = None
    # One-sentence TLDR strip rendered on the intro slide (slide 1) below
    # the subtitle. None when the intro has no strip.
    tldr_strip: str | None = None


def style_display_name(model: str, style: str) -> str:
    """Render the (model, style) tuple as a human-readable preset name."""
    return IMAGE_PRESET_DISPLAY.get((model, style), f"{model}/{style}")


def short_scene(scene: str, max_chars: int = 80) -> str:
    """Trim a scene description to the first max_chars chars on a word boundary."""
    cleaned = scene.strip().replace("\n", " ")
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"


def pack_extras(slide_data: SlideData) -> dict[str, object] | None:
    """Bundle features/stats/insight + EN translation into a JSON dict."""
    payload: dict[str, object] = {
        field: value for field in EXTRAS_FIELDS if (value := getattr(slide_data, field))
    }
    return payload or None


def build_slides_en_index(raw: object) -> dict[int, dict[str, object]]:
    """Index the optional `slides_en` array by slide number for fast lookup.

    Tolerates the field being absent or malformed (LLM may skip it).
    Each EN slide carries: heading, body, features?, stats?, insight?,
    summary_points?, tldr_strip?
    """
    result: dict[int, dict[str, object]] = {}
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if not isinstance(number, int):
            continue
        result[number] = {
            "heading": str(item.get("heading") or ""),
            "body": str(item.get("body") or ""),
            "features": item.get("features"),
            "stats": item.get("stats"),
            "insight": item.get("insight"),
            "summary_points": item.get("summary_points"),
            "tldr_strip": item.get("tldr_strip"),
        }
    return result


def unpack_extras(slide: CarouselSlide) -> SlideData:
    """Hydrate a SlideData from a persisted CarouselSlide.

    Used by the refine re-render path so the new HTML carries the same
    structured cards (features/stats/insight/summary_points/tldr_strip)
    as the original render.
    """
    extras = slide.extras or {}
    features = extras.get("features") if isinstance(extras, dict) else None
    stats = extras.get("stats") if isinstance(extras, dict) else None
    insight = extras.get("insight") if isinstance(extras, dict) else None
    translation_en = extras.get("translation_en") if isinstance(extras, dict) else None
    summary_points = extras.get("summary_points") if isinstance(extras, dict) else None
    tldr_strip = extras.get("tldr_strip") if isinstance(extras, dict) else None
    image_prompt = slide.image_prompt or (
        extras.get("image_prompt") if isinstance(extras, dict) else None
    )
    return SlideData(
        slide_number=slide.slide_number,
        slide_type=slide.slide_type,
        heading=slide.heading,
        body=slide.body,
        image_prompt=image_prompt if isinstance(image_prompt, str) else None,
        features=features if isinstance(features, list) else None,
        stats=stats if isinstance(stats, list) else None,
        insight=insight if isinstance(insight, dict) else None,
        translation_en=(translation_en if isinstance(translation_en, dict) else None),
        summary_points=summary_points if isinstance(summary_points, list) else None,
        tldr_strip=str(tldr_strip) if tldr_strip else None,
    )


def slides_data_for_language(slides: list[SlideData], language: str) -> list[SlideData]:
    """Return a copy of slides with text overridden to the target language.

    For 'pt' we return the originals untouched. For 'en' we swap heading,
    body, features, stats, insight, summary_points, tldr_strip from
    `translation_en` when present.
    """
    if language == "pt":
        return slides

    swapped: list[SlideData] = []
    for sd in slides:
        en = sd.translation_en
        if not en:
            swapped.append(sd)
            continue
        en_features = en.get("features") if isinstance(en, dict) else None
        en_stats = en.get("stats") if isinstance(en, dict) else None
        en_insight = en.get("insight") if isinstance(en, dict) else None
        en_summary_points = en.get("summary_points") if isinstance(en, dict) else None
        en_tldr_strip = en.get("tldr_strip") if isinstance(en, dict) else None
        swapped.append(
            SlideData(
                slide_number=sd.slide_number,
                slide_type=sd.slide_type,
                heading=str(en.get("heading") or sd.heading),
                body=str(en.get("body") or sd.body),
                image_prompt=sd.image_prompt,
                features=en_features if isinstance(en_features, list) else sd.features,
                stats=en_stats if isinstance(en_stats, list) else sd.stats,
                insight=en_insight if isinstance(en_insight, dict) else sd.insight,
                translation_en=sd.translation_en,
                summary_points=en_summary_points
                if isinstance(en_summary_points, list)
                else sd.summary_points,
                tldr_strip=str(en_tldr_strip) if en_tldr_strip else sd.tldr_strip,
            )
        )
    return swapped
