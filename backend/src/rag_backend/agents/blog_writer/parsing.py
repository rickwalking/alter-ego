"""Parse the blog writer's JSON into domain value objects (AE-0425).

A structural problem raises ``ValueError`` so ``ainvoke_json`` re-rolls /
repairs / falls back before the writer gives up. Headings lose any leading
``#`` (the document stores plain-text headings), bodies lose a leading H1 and
HTML tags (raw HTML is never rendered) and keep their markdown.
"""

from __future__ import annotations

import re

from rag_backend.agents.blog_writer.constants import (
    ERR_BAD_ARTICLE,
    KEY_BODY_MD,
    KEY_EN,
    KEY_HEADING,
    KEY_NOTES,
    KEY_SECTIONS,
    KEY_TITLE,
    MAX_JUDGE_NOTES,
)
from rag_backend.domain.copy_sanitize import sanitize_model_copy
from rag_backend.domain.models.blog_generation import DraftArticle, DraftSection
from rag_backend.infrastructure.llm.json_utils import extract_json

_LEADING_H1 = re.compile(r"\A\s*#\s+[^\n]*\n?")
_HTML_TAG = re.compile(r"<[a-zA-Z/!][^<>]*>")
_HEADING_MARKS = "# \t"


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(ERR_BAD_ARTICLE)
    return value


def _heading(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = sanitize_model_copy(_HTML_TAG.sub("", value)).lstrip(_HEADING_MARKS)
    return cleaned.strip() or None


def _body(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(ERR_BAD_ARTICLE)
    without_h1 = _LEADING_H1.sub("", value, count=1)
    return sanitize_model_copy(_HTML_TAG.sub("", without_h1))


def parse_sections(value: object) -> tuple[DraftSection, ...]:
    """The non-empty sections of a ``sections`` array (raises if none)."""
    if not isinstance(value, list):
        raise TypeError(ERR_BAD_ARTICLE)
    sections = tuple(
        DraftSection(
            heading=_heading(item.get(KEY_HEADING)),
            body_md=_body(item.get(KEY_BODY_MD)),
        )
        for item in (_object(raw) for raw in value)
    )
    usable = tuple(section for section in sections if section.body_md.strip())
    if not usable:
        raise ValueError(ERR_BAD_ARTICLE)
    return usable


def _title(payload: dict[str, object]) -> str:
    title = payload.get(KEY_TITLE)
    return _heading(title) or ""


def parse_draft(raw: str) -> DraftArticle:
    """``{"title", "sections", "en": {"title", "sections"}}`` → :class:`DraftArticle`."""
    payload = _object(extract_json(raw))
    english = _object(payload.get(KEY_EN))
    return DraftArticle(
        title=_title(payload),
        sections=parse_sections(payload.get(KEY_SECTIONS)),
        en_title=_title(english),
        en_sections=parse_sections(english.get(KEY_SECTIONS)),
    )


def parse_rewrite(raw: str) -> tuple[DraftSection, ...]:
    """``{"sections": [...]}`` → the rewritten sections."""
    return parse_sections(_object(extract_json(raw)).get(KEY_SECTIONS))


def parse_notes(raw: str) -> tuple[str, ...]:
    """``{"notes": [...]}`` → at most ``MAX_JUDGE_NOTES`` non-blank notes."""
    notes = _object(extract_json(raw)).get(KEY_NOTES)
    if not isinstance(notes, list):
        raise TypeError(ERR_BAD_ARTICLE)
    cleaned = (sanitize_model_copy(note) for note in notes if isinstance(note, str))
    return tuple(note for note in cleaned if note)[:MAX_JUDGE_NOTES]


__all__ = ["parse_draft", "parse_notes", "parse_rewrite", "parse_sections"]
