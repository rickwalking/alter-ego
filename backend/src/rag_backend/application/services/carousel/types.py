"""Shared types + helpers for the carousel pipeline.

Lifted during the LangGraph refactor so workflow nodes and refinement
service share the same data shapes without circular imports. Pure-data / pure-function module — no side effects,
no repository or LLM dependencies.

Feature cards are capped at 4 because the ``.feature-grid`` CSS is tuned for 2-4 items
and 5 or more overflow the slide footer. A carousel holds at most 10 slides, Instagram's
limit, so the POV contract (8-10 slides) fits; the fixed 7-slide decks keep
``LEGACY_SLIDE_COUNT``. ``IMAGE_PRESET_DISPLAY`` gives the preset name shown in the
phase-progress label during image generation.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TypedDict

from rag_backend.application.services.carousel.presentation_copy_repair import (
    repair_text_sentence_case_en,
)
from rag_backend.domain.models import CarouselSlide

MAX_FEATURE_ITEMS = 4

MAX_SLIDES = 10
LEGACY_SLIDE_COUNT = 7

EXTRAS_FIELDS: tuple[str, ...] = (
    "features",
    "stats",
    "insight",
    "image_prompt",
    "translation_en",
    "summary_points",
    "tldr_strip",
    "long_form_notes",
)

IMAGE_PRESET_DISPLAY: dict[tuple[str, str], str] = {
    ("openai", "comic_neon"): "OpenAI Comic Neon",
    ("openai", "cinematic"): "OpenAI Cinematic Photoreal",
    ("openai", "hyperreal"): "OpenAI Hyperreal Graphic Novel",
    ("openai", "neo_anime"): "OpenAI Neo-Anime",
    ("openai", "flat_editorial"): "OpenAI Flat Editorial",
    ("openai", "pov_editorial"): "OpenAI Foto + Editorial (POV)",
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
    """Structured slide data from content synthesis.

    ``features`` are checklist items for closing and feature slides (``{"icon", "title",
    "body"}``); ``stats`` are big-number cards in a 3-column grid (``{"value", "label",
    "detail"}``); ``insight`` is one quote with attribution in an accent-bordered card.
    ``translation_en`` is the EN counterpart of heading, body, features, stats and
    insight; None means EN renders fall back to PT. ``summary_points`` are the three
    snapshot cards of the summary slide, ``tldr_strip`` is the one-sentence strip under
    the intro subtitle, and ``long_form_notes`` are extended notes for the blog,
    separate from the constrained slide copy.
    """

    slide_number: int
    slide_type: str
    heading: str
    body: str
    image_prompt: str | None = None
    features: list[dict[str, str]] | None = None
    stats: list[dict[str, str]] | None = None
    insight: dict[str, str] | None = None
    translation_en: dict[str, object] | None = None
    summary_points: list[dict[str, str]] | None = None
    tldr_strip: str | None = None
    long_form_notes: str | None = None


def slide_count_from_config(slides_config: str) -> int:
    cleaned = slides_config.strip().lower()
    parts = [p.strip() for p in cleaned.replace("_slides", "").split(",")]
    if len(parts) == 1:
        try:
            return int(parts[0])
        except ValueError:
            pass
    total = 0
    for part in parts:
        with suppress(ValueError, IndexError):
            total += int(part.split()[0])
    return total if total > 0 else LEGACY_SLIDE_COUNT


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
    long_form_notes = (
        extras.get("long_form_notes") if isinstance(extras, dict) else None
    )
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
        long_form_notes=str(long_form_notes) if long_form_notes else None,
    )


def slides_data_for_language(slides: list[SlideData], language: str) -> list[SlideData]:
    """Return a copy of slides with text overridden to the target language.

    For 'pt' we return the originals untouched. For 'en' we swap heading,
    body, features, stats, insight, summary_points, tldr_strip from
    `translation_en` when present.

    The ``translation_en`` payload is the EN render source, so the EN sentence-case
    repair is applied here: all-lowercase EN copy cannot reach the renderer even when
    the localized-slides repair path was bypassed.
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
        en_heading = repair_text_sentence_case_en(str(en.get("heading") or sd.heading))
        en_body = repair_text_sentence_case_en(str(en.get("body") or sd.body))
        swapped.append(
            SlideData(
                slide_number=sd.slide_number,
                slide_type=sd.slide_type,
                heading=en_heading,
                body=en_body,
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
