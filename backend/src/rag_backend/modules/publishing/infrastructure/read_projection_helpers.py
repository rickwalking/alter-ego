"""Markdown title/subtitle/body helpers for the publishing read projection (AE-0131).

These pure functions replicate the legacy carousel-blog route helpers
(``api/routes/carousels/helpers.py``: ``_extract_title_and_subtitle`` /
``_extract_first_paragraph``) byte-identically so the carousel-blog i18n
projection produces the same title/subtitle resolution. They live in the
publishing infrastructure (not imported from ``api``) so the read ACL stays
within the module's own seam (no ``infrastructure -> api`` import).

``resolve_blog_body`` is the AE-0127 backfill resolution: it prefers the
``origin='carousel'`` blog row's body when present and falls back to the embedded
carousel ``blog_markdown`` column, so the response is byte-identical (no embedded
column is dropped).
"""

from __future__ import annotations

from typing import cast

# Title/subtitle heading separator — identical to the legacy helper.
_TITLE_SUBTITLE_SEPARATOR = ":"
_FIRST_PARAGRAPH_MAX_LEN = 200
# Keys read out of a backfilled blog row's JSON ``content`` body, in priority
# order, when resolving the rendered markdown for the carousel-blog projection.
_BODY_CONTENT_KEYS = ("markdown", "body")


def extract_title_and_subtitle(markdown: str) -> tuple[str | None, str | None]:
    """Split the markdown ``# Heading: Subtitle`` line (legacy helper, identical)."""
    lines = markdown.strip().split("\n")
    if not lines:
        return None, None
    first_line = lines[0]
    if not first_line.startswith("# "):
        return None, None
    heading = first_line[2:].strip()
    if _TITLE_SUBTITLE_SEPARATOR in heading:
        separator_pos = heading.index(_TITLE_SUBTITLE_SEPARATOR)
        title = heading[:separator_pos].strip()
        subtitle = heading[separator_pos + 1 :].strip()
        return title, subtitle
    return heading, None


def extract_first_paragraph(markdown: str) -> str | None:
    """Return the first non-heading paragraph, truncated (legacy helper, identical)."""
    lines = markdown.strip().split("\n")
    paragraphs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped:
            paragraphs.append(stripped)
        elif paragraphs:
            break
    if not paragraphs:
        return None
    return " ".join(paragraphs)[:_FIRST_PARAGRAPH_MAX_LEN]


def resolve_blog_body(
    row_content: object,
    embedded_markdown: str | None,
) -> str | None:
    """Resolve the carousel-blog markdown (AE-0127 backfill, embedded fallback).

    Prefers the ``origin='carousel'`` backfill row's rendered body (the row's JSON
    ``content``, passed in by the read ACL — this helper stays ORM-free) when it
    carries one, falling back to the embedded carousel ``blog_markdown`` column so
    the response stays byte-identical. Returns ``None`` when neither provides a body
    (the route maps that to the legacy 404).
    """
    body = _body_from_content(row_content)
    if body is not None:
        return body
    return embedded_markdown


def _body_from_content(content: object) -> str | None:
    """Extract a rendered markdown body from a backfill row's JSON ``content``."""
    if not isinstance(content, dict):
        return None
    typed_content = cast("dict[str, object]", content)
    for key in _BODY_CONTENT_KEYS:
        value = typed_content.get(key)
        if isinstance(value, str) and value:
            return value
    return None


__all__ = [
    "extract_first_paragraph",
    "extract_title_and_subtitle",
    "resolve_blog_body",
]
