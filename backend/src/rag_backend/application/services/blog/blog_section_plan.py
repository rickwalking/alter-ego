"""How many sections a generated post has, and the role of each (AE-0425).

Owner revision of ADR-0025: the section count is the carousel's slide count,
never a blog-only maximum. :func:`resolve_section_count` applies the order
``project.slide_count`` → the real deck size (the slide rows, CTA included;
AE-0439) → ``slide_count_from_config(slides_config)`` → the content-mode
default (standalone posts have no project and use that default).
:func:`normalize_section_count` makes a writer that missed the count either fit
exactly N sections (merge extras / split long sections on paragraph breaks)
or fail with :class:`SectionCountMismatchError` — a wrong count is never stored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_backend.application.services.carousel.types import slide_count_from_config
from rag_backend.domain.constants.blog_generation import ERR_SECTION_COUNT_MISMATCH
from rag_backend.domain.constants.blog_voice import MIDDLE_ROLES, ROLE_CLOSE, ROLE_LEDE
from rag_backend.domain.constants.content_mode import (
    DEFAULT_CONTENT_MODE,
    NEWS_SLIDE_COUNT_MIN,
    POV_FAMILY_MODES,
    POV_SLIDE_COUNT_DEFAULT,
)
from rag_backend.domain.models.blog_generation import (
    DraftSection,
    SectionCountMismatchError,
)

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_PARAGRAPH_JOIN = "\n\n"
_MIN_PARAGRAPHS_TO_SPLIT = 2


@dataclass(frozen=True)
class SectionCountSource:
    """The carousel fields the count is derived from (all optional).

    ``deck_slide_count`` is the REAL deck size (the persisted slide rows,
    CTA included). AE-0439 (QA F-07): a Radar IA create stored no
    ``slide_count`` and the legacy ``slides_config`` (6) predates the v4
    contract, so the real deck size must come first.
    """

    slide_count: int | None = None
    deck_slide_count: int | None = None
    slides_config: str | None = None
    content_mode: str | None = None


def default_section_count(content_mode: str | None) -> int:
    """The content-mode default deck size (POV 9, Radar IA 7)."""
    mode = content_mode or DEFAULT_CONTENT_MODE
    if mode in POV_FAMILY_MODES:
        return POV_SLIDE_COUNT_DEFAULT
    return NEWS_SLIDE_COUNT_MIN


def resolve_section_count(source: SectionCountSource) -> int:
    """``slide_count`` → real deck size → ``slides_config`` → mode default.

    AE-0439: the order is the stored count first, then the real deck size
    (the slide rows, CTA included), then the legacy config, then the
    content-mode default (standalone posts have no project and use that
    default). The CTA slide counts as a section (ADR-0025 §Count).
    """
    if source.slide_count is not None and source.slide_count > 0:
        return source.slide_count
    if source.deck_slide_count is not None and source.deck_slide_count > 0:
        return source.deck_slide_count
    if source.slides_config and source.slides_config.strip():
        return slide_count_from_config(source.slides_config)
    return default_section_count(source.content_mode)


def narrative_roles(count: int) -> tuple[str, ...]:
    """One distinct role per section: lede, the middle roles, then the close."""
    if count <= 1:
        return (ROLE_LEDE,)
    middle = tuple(
        MIDDLE_ROLES[index % len(MIDDLE_ROLES)] for index in range(count - 2)
    )
    return (ROLE_LEDE, *middle, ROLE_CLOSE)


def _paragraphs(body: str) -> list[str]:
    return [part.strip() for part in _PARAGRAPH_SPLIT.split(body) if part.strip()]


def _merge_tail(sections: list[DraftSection], count: int) -> list[DraftSection]:
    head, tail = sections[: count - 1], sections[count - 1 :]
    body = _PARAGRAPH_JOIN.join(section.body_md.strip() for section in tail)
    return [*head, DraftSection(heading=tail[0].heading, body_md=body)]


def _split_once(sections: list[DraftSection]) -> list[DraftSection]:
    sizes = [len(_paragraphs(section.body_md)) for section in sections]
    index = max(range(len(sections)), key=lambda position: sizes[position])
    if sizes[index] < _MIN_PARAGRAPHS_TO_SPLIT:
        raise SectionCountMismatchError(ERR_SECTION_COUNT_MISMATCH)
    paragraphs = _paragraphs(sections[index].body_md)
    middle = len(paragraphs) // 2
    first = DraftSection(
        heading=sections[index].heading,
        body_md=_PARAGRAPH_JOIN.join(paragraphs[:middle]),
    )
    second = DraftSection(
        heading=None, body_md=_PARAGRAPH_JOIN.join(paragraphs[middle:])
    )
    return [*sections[:index], first, second, *sections[index + 1 :]]


def normalize_section_count(
    sections: tuple[DraftSection, ...], count: int
) -> tuple[DraftSection, ...]:
    """Exactly ``count`` sections, or :class:`SectionCountMismatchError`."""
    if not sections or count < 1:
        raise SectionCountMismatchError(ERR_SECTION_COUNT_MISMATCH)
    normalized = list(sections)
    if len(normalized) > count:
        normalized = _merge_tail(normalized, count)
    while len(normalized) < count:
        normalized = _split_once(normalized)
    return tuple(normalized)


__all__ = [
    "SectionCountSource",
    "default_section_count",
    "narrative_roles",
    "normalize_section_count",
    "resolve_section_count",
]
