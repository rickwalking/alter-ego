"""Markdown title/subtitle/body helpers for the publishing read projection.

These pure functions replicate the legacy carousel-blog route helpers
(``api/routes/carousels/helpers.py``: ``_extract_title_and_subtitle`` /
``_extract_first_paragraph``) byte-identically so the carousel-blog i18n
projection produces the same title/subtitle resolution. They live in the
publishing infrastructure (not imported from ``api``) so the read ACL stays
within the module's own seam (no ``infrastructure -> api`` import).

``resolve_blog_body`` sources the carousel-blog markdown SOLELY from the
``origin='carousel'`` ``blog_posts`` row. The embedded
``carousel_projects.blog_markdown`` column is no longer read: the
carousel repository dual-writes the canonical row on every blog write, and the backfill
covered every pre-existing public/completed carousel, so the row is always
present whenever the legacy embedded column was non-null — the response stays
byte-identical (the snapshot safety net) and the column is now WRITE-dead, ready for the
column drop.

The rendered markdown is resolved from a backfilled blog row's JSON ``content`` body by
trying a fixed list of keys in priority order.
"""

from __future__ import annotations

from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

_TITLE_SUBTITLE_SEPARATOR = ":"
_FIRST_PARAGRAPH_MAX_LEN = 200
_BODY_CONTENT_KEYS = ("markdown", "body")


def as_number(value: object) -> float:
    """Narrow a summary value to a number for the typed projection (no ``Any``)."""
    if isinstance(value, (int, float)):
        return value
    return 0.0


def as_optional_number(value: object) -> float | None:
    """Like :func:`as_number`, but an absent value stays ``None``."""
    if value is None:
        return None
    return float(as_number(value))


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


def resolve_blog_body(row: BlogPostModel | None) -> str | None:
    """Resolve the carousel-blog markdown from the ``origin='carousel'`` row.

    Sources the rendered body SOLELY from the canonical backfill/dual-write row;
    the embedded ``carousel_projects.blog_markdown`` column is no longer read.
    Returns ``None`` when the row is absent or carries no body (the route maps that
    to the legacy 404). The row is guaranteed present whenever the legacy embedded
    column was non-null (backfill + dual-write), so the response
    stays byte-identical.
    """
    return _body_from_row(row)


def _body_from_row(row: BlogPostModel | None) -> str | None:
    """Extract a rendered markdown body from a backfill row's JSON content.

    ``content`` is a JSON object (``dict[str, object]``) by construction — the
    backfill, the dual-write, and ``from_entity`` all store a dict.
    Returns the first non-empty string body key, or ``None`` (the legacy 404).
    """
    if row is None:
        return None
    for key in _BODY_CONTENT_KEYS:
        value = row.content.get(key)
        if isinstance(value, str) and value:
            return value
    return None


__all__ = [
    "as_number",
    "as_optional_number",
    "extract_first_paragraph",
    "extract_title_and_subtitle",
    "resolve_blog_body",
]
