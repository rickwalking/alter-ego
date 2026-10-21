"""Build the writer brief of a generation request (ADR-0025).

From a carousel, the brief carries the frozen artifact as *raw material*: the
research findings (summary + key points per source) and the outline from the
workflow checkpoint, and the per-slide ``long_form_notes`` from the persisted
slide rows. Nothing is concatenated into the body: the writer composes one
article from it. Standalone generation has only a topic (+ source URLs, which
are passed as references and never fetched).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.blog.blog_section_plan import narrative_roles
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    LONG_FORM_NOTES_KEY,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_KEY_POINTS,
    OUTLINE_FIELD_TITLE,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_OUTLINE,
    STATE_FIELD_RESEARCH_FINDINGS,
)
from rag_backend.domain.models.blog_generation import OutlinePoint, WriterBrief
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.domain.models.persona import PersonaProfile

_FINDING_SUMMARY = "summary"
_FINDING_KEY_POINTS = "key_points"
_KEY_POINT_JOIN = " "


@dataclass(frozen=True)
class CarouselMaterial:
    """What a carousel contributes to its blog post."""

    title: str
    topic: str
    persona: PersonaProfile
    section_count: int
    slides: tuple[CarouselSlide, ...] = ()
    state: Mapping[str, object] | None = None


@dataclass(frozen=True)
class StandaloneMaterial:
    """A standalone request: a topic, a persona and optional references."""

    topic: str
    persona: PersonaProfile
    section_count: int
    source_urls: tuple[str, ...] = ()


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _dicts(state: Mapping[str, object] | None, key: str) -> list[Mapping[str, object]]:
    raw = state.get(key) if state is not None else None
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _finding_text(finding: Mapping[str, object]) -> str:
    summary = finding.get(_FINDING_SUMMARY)
    parts = [summary.strip()] if isinstance(summary, str) and summary.strip() else []
    parts.extend(_strings(finding.get(_FINDING_KEY_POINTS)))
    return _KEY_POINT_JOIN.join(parts)


def research_material(state: Mapping[str, object] | None) -> tuple[str, ...]:
    """One text per research source (summary + key points), blanks dropped."""
    texts = (
        _finding_text(item) for item in _dicts(state, STATE_FIELD_RESEARCH_FINDINGS)
    )
    return tuple(dict.fromkeys(text for text in texts if text))


def outline_material(state: Mapping[str, object] | None) -> tuple[OutlinePoint, ...]:
    """The outline items that have a title."""
    points = (
        OutlinePoint(
            title=str(item.get(OUTLINE_FIELD_TITLE) or "").strip(),
            key_points=_strings(item.get(OUTLINE_FIELD_KEY_POINTS)),
        )
        for item in _dicts(state, STATE_FIELD_OUTLINE)
    )
    return tuple(point for point in points if point.title)


def notes_material(slides: tuple[CarouselSlide, ...]) -> tuple[str, ...]:
    """The non-blank ``long_form_notes`` of the slides, in slide order."""
    ordered = sorted(slides, key=lambda slide: slide.slide_number)
    notes = ((slide.extras or {}).get(LONG_FORM_NOTES_KEY) for slide in ordered)
    return tuple(
        note.strip() for note in notes if isinstance(note, str) and note.strip()
    )


def carousel_brief(material: CarouselMaterial) -> WriterBrief:
    """The brief of a carousel-origin post (N = the carousel slide count)."""
    return WriterBrief(
        title=material.title,
        topic=material.topic,
        section_roles=narrative_roles(material.section_count),
        persona=material.persona,
        research=research_material(material.state),
        outline=outline_material(material.state),
        notes=notes_material(material.slides),
    )


def standalone_brief(material: StandaloneMaterial) -> WriterBrief:
    """The brief of a standalone post (N = the content-mode default)."""
    return WriterBrief(
        title=material.topic,
        topic=material.topic,
        section_roles=narrative_roles(material.section_count),
        persona=material.persona,
        source_urls=material.source_urls,
    )


__all__ = [
    "CarouselMaterial",
    "StandaloneMaterial",
    "carousel_brief",
    "notes_material",
    "outline_material",
    "research_material",
    "standalone_brief",
]
