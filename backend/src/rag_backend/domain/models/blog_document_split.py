"""Fence-aware v1 markdown <-> ``blog.v2`` conversion (AE-0423, ADR-0025).

Pure functions shared by the one-shot cutover command and the temporary read
fail-safe, so both split a legacy body with exactly the same rules:

- a section starts at a ``## `` line **outside** fenced code blocks;
- a leading ``# <title>`` line of the lede is stripped (the title is a column);
- an empty lede chunk is dropped; a headed chunk is kept even with no body;
- bodies are stored **raw** (no sanitization) minus the surrounding newlines;
- a document always ends with >= 1 section;
- ``cover``/``image``/``quality`` are ``None`` (v1 never stored images).

``join_language_document`` is the ``--rollback`` inverse: it re-joins
``## {heading}\\n\\n{body_md}`` so section body bytes round-trip exactly.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    BLOG_SECTION_ID_PREFIX,
    KEY_BODY_MD,
    KEY_COVER,
    KEY_HEADING,
    KEY_ID,
    KEY_IMAGE,
    KEY_QUALITY,
    KEY_SCHEMA,
    KEY_SECTIONS,
    KEY_TRANSLATIONS,
    LEGACY_KEY_BODY,
    LEGACY_KEY_MARKDOWN,
)

SectionIdFactory = Callable[[], str]

_H2_RE = re.compile(r"^## ")
_H1_RE = re.compile(r"^# ")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_LINE_BREAKS = "\r\n"
_SECTION_SEPARATOR = "\n\n"
_H2_PREFIX = "## "


def new_section_id() -> str:
    """Mint a fresh, stable ``sec_<uuid4>`` section id."""
    return f"{BLOG_SECTION_ID_PREFIX}{uuid.uuid4()}"


@dataclass(frozen=True)
class MarkdownChunk:
    """One split chunk: ``heading`` is ``None`` for the lede."""

    heading: str | None
    body: str


@dataclass
class _FenceState:
    marker: str = ""

    def update(self, line: str) -> None:
        match = _FENCE_RE.match(line)
        if match is None:
            return
        fence, rest = match.group(1), match.group(2)
        if not self.marker:
            self.marker = fence
            return
        # CommonMark: a closing fence repeats the opening char, is at least as
        # long, and carries no info string (```python inside a fence is code).
        closes = fence[0] == self.marker[0] and len(fence) >= len(self.marker)
        if closes and not rest.strip():
            self.marker = ""

    @property
    def open(self) -> bool:
        return bool(self.marker)


def _is_boundary(line: str, fence: _FenceState) -> bool:
    return not fence.open and _H2_RE.match(line) is not None


def _group_lines(markdown: str) -> list[tuple[str | None, list[str]]]:
    groups: list[tuple[str | None, list[str]]] = [(None, [])]
    fence = _FenceState()
    for line in markdown.splitlines(keepends=True):
        if _is_boundary(line, fence):
            groups.append((line[len(_H2_PREFIX) :].strip(), []))
            continue
        fence.update(line)
        groups[-1][1].append(line)
    return groups


def _strip_leading_h1(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if _H1_RE.match(line) is None:
            return lines
        return lines[:index] + lines[index + 1 :]
    return lines


def split_markdown(markdown: str) -> list[MarkdownChunk]:
    """Split on ``## `` outside fences; strip the lede H1; drop an empty lede."""
    groups = _group_lines(markdown)
    lede_heading, lede_lines = groups[0]
    groups[0] = (lede_heading, _strip_leading_h1(lede_lines))
    chunks = [
        MarkdownChunk(heading=heading, body="".join(lines).strip(_LINE_BREAKS))
        for heading, lines in groups
    ]
    if not chunks[0].body.strip():
        chunks = chunks[1:]
    return chunks


def _section(chunk: MarkdownChunk, new_id: SectionIdFactory) -> dict[str, object]:
    return {
        KEY_ID: new_id(),
        KEY_HEADING: chunk.heading,
        KEY_BODY_MD: chunk.body,
        KEY_IMAGE: None,
    }


def build_language_document(
    markdown: str, new_id: SectionIdFactory = new_section_id
) -> dict[str, object]:
    """Convert one language's flat markdown into a v2 language document."""
    chunks = split_markdown(markdown) or [MarkdownChunk(heading=None, body="")]
    return {
        KEY_SCHEMA: BLOG_SCHEMA_V2,
        KEY_COVER: None,
        KEY_SECTIONS: [_section(chunk, new_id) for chunk in chunks],
        KEY_QUALITY: None,
    }


def extract_legacy_markdown(content: object) -> str:
    """The v1 markdown string, or ``""`` — never ``str(dict)`` garbage."""
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return ""
    for key in (LEGACY_KEY_MARKDOWN, LEGACY_KEY_BODY):
        value = content.get(key)
        if isinstance(value, str):
            return value
    return ""


def _is_markdown_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def legacy_translations(content: object) -> dict[str, str]:
    """Non-blank string translations of a v1 row.

    Non-string entries are dropped (never ``str(dict)``) and so are blank
    strings: v1 rendered PT for an empty translation, so the cutover must not
    turn it into an empty EN document that would hide the PT fallback.
    """
    if not isinstance(content, dict):
        return {}
    raw = content.get(KEY_TRANSLATIONS)
    if not isinstance(raw, dict):
        return {}
    return {
        str(lang): str(value) for lang, value in raw.items() if _is_markdown_text(value)
    }


def is_v2_language_document(value: object) -> bool:
    """Whether ``value`` carries the ``blog.v2`` schema marker."""
    return isinstance(value, dict) and value.get(KEY_SCHEMA) == BLOG_SCHEMA_V2


def is_v2_content(content: object) -> bool:
    """Top level AND every translation value are at ``blog.v2``."""
    if not isinstance(content, dict) or not is_v2_language_document(content):
        return False
    translations = content.get(KEY_TRANSLATIONS, {})
    if not isinstance(translations, dict):
        return False
    return all(is_v2_language_document(value) for value in translations.values())


def _migrate_translations(raw: object, new_id: SectionIdFactory) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    migrated: dict[str, object] = {}
    for lang, value in raw.items():
        if is_v2_language_document(value):
            migrated[str(lang)] = value
        elif isinstance(value, str) and _is_markdown_text(value):
            migrated[str(lang)] = build_language_document(value, new_id)
    return migrated


def convert_legacy_content(
    content: object, new_id: SectionIdFactory = new_section_id
) -> dict[str, object]:
    """Rewrite a v1 ``content`` (PT + every string translation) to ``blog.v2``."""
    document = build_language_document(extract_legacy_markdown(content), new_id)
    document[KEY_TRANSLATIONS] = {
        lang: build_language_document(markdown, new_id)
        for lang, markdown in legacy_translations(content).items()
    }
    return document


def migrate_content(
    content: object, new_id: SectionIdFactory = new_section_id
) -> dict[str, object] | None:
    """The v2 rewrite of ``content``, or ``None`` when it is already v2 (no-op).

    A top-level v2 row whose translations are not all v2 keeps its PT document
    and only has the stray translation values converted (strings) or dropped.
    """
    if is_v2_content(content):
        return None
    if isinstance(content, dict) and is_v2_language_document(content):
        fixed = dict(content)
        fixed[KEY_TRANSLATIONS] = _migrate_translations(
            content.get(KEY_TRANSLATIONS), new_id
        )
        return fixed
    return convert_legacy_content(content, new_id)


def _join_section(section: object) -> str:
    if not isinstance(section, dict):
        return ""
    body = section.get(KEY_BODY_MD)
    body_text = body if isinstance(body, str) else ""
    heading = section.get(KEY_HEADING)
    if not isinstance(heading, str):
        return body_text
    return f"{_H2_PREFIX}{heading}{_SECTION_SEPARATOR}{body_text}"


def join_language_document(document: object) -> str:
    """Re-join a v2 language document into flat markdown (``--rollback``)."""
    if not isinstance(document, dict):
        return ""
    sections = document.get(KEY_SECTIONS)
    if not isinstance(sections, list):
        return ""
    return _SECTION_SEPARATOR.join(_join_section(section) for section in sections)


def rollback_content(content: object) -> dict[str, object]:
    """The v1 shape ``{"markdown": ..., "translations": {lang: markdown}}``."""
    raw = content.get(KEY_TRANSLATIONS) if isinstance(content, dict) else None
    translations: dict[str, object] = {}
    if isinstance(raw, dict):
        translations = {
            str(lang): join_language_document(doc) for lang, doc in raw.items()
        }
    return {
        LEGACY_KEY_MARKDOWN: join_language_document(content),
        KEY_TRANSLATIONS: translations,
    }


__all__ = [
    "MarkdownChunk",
    "SectionIdFactory",
    "build_language_document",
    "convert_legacy_content",
    "extract_legacy_markdown",
    "is_v2_content",
    "is_v2_language_document",
    "join_language_document",
    "legacy_translations",
    "migrate_content",
    "new_section_id",
    "rollback_content",
    "split_markdown",
]
