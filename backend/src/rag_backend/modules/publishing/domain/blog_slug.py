"""Server-side slug generation for hand-authored blog posts.

``blog_posts.slug`` is ``UNIQUE NOT NULL``. A create request without a slug used
to persist ``""``, so every create after the first slug-less post hit the unique
constraint (409 "New Post"). The service now derives a slug from the title plus a
short random suffix, so two posts with the same title still get distinct slugs.

NFKD splits accented letters into base letter and combining mark so the marks can be
dropped (“Revisão” becomes “revisao”). The title part is kept short so the slug stays
readable and well under 255 characters.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Final, Literal

_NORMAL_FORM: Final[Literal["NFKD"]] = "NFKD"
_ASCII = "ascii"
_IGNORE = "ignore"
_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")
_SLUG_SEPARATOR = "-"
_FALLBACK_STEM = "post"
_MAX_STEM_LENGTH = 80
_SUFFIX_LENGTH = 8
_SLUG_KEY = "slug"
_TITLE_KEY = "title"


def slugify_title(title: str) -> str:
    """Lowercase ASCII stem of ``title`` (accents dropped, runs of others → ``-``)."""
    decomposed = unicodedata.normalize(_NORMAL_FORM, title.lower())
    ascii_text = decomposed.encode(_ASCII, _IGNORE).decode(_ASCII)
    stem = _NON_SLUG_CHARS.sub(_SLUG_SEPARATOR, ascii_text).strip(_SLUG_SEPARATOR)
    stem = stem[:_MAX_STEM_LENGTH].rstrip(_SLUG_SEPARATOR)
    return stem or _FALLBACK_STEM


def build_blog_slug(title: str, suffix: str) -> str:
    """Join the title stem and ``suffix`` (``"my-title-1a2b3c4d"``)."""
    return f"{slugify_title(title)}{_SLUG_SEPARATOR}{suffix}"


def new_slug_suffix() -> str:
    """Short random suffix that keeps same-title slugs distinct."""
    return uuid.uuid4().hex[:_SUFFIX_LENGTH]


def with_generated_slug(payload: dict[str, object]) -> dict[str, object]:
    """Return ``payload`` with a generated slug when none (or a blank one) is given.

    A caller-supplied non-blank slug is kept as-is (stripped); a clash on it is
    reported by the route as a 409 ``blog_post_slug_conflict``.
    """
    given = payload.get(_SLUG_KEY)
    if isinstance(given, str) and given.strip():
        return {**payload, _SLUG_KEY: given.strip()}
    title = payload.get(_TITLE_KEY)
    stem_source = title if isinstance(title, str) else ""
    return {**payload, _SLUG_KEY: build_blog_slug(stem_source, new_slug_suffix())}


__all__ = [
    "build_blog_slug",
    "new_slug_suffix",
    "slugify_title",
    "with_generated_slug",
]
