"""Domain-level constants for blog post management.

Every ``BlogPostOrigin`` member appears in exactly one hard-delete policy set (a unit
test enforces it, so a new origin cannot ship without a policy). Link-guarded origins
back another public surface: their hard delete is blocked (409) while ``project_id`` is
set, because deleting the row would 404 the public carousel blog projection; once the
parent project is deleted the detached row is hard-deletable. A slug conflict means a
caller-supplied slug is already in use (generated slugs carry a random suffix). The
forbidden phrases are the persona-training defaults.
"""

from enum import StrEnum


class BlogPostStatus(StrEnum):
    """Blog post workflow status values."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EditorialCommentStatus(StrEnum):
    """Editorial comment status values."""

    OPEN = "open"
    RESOLVED = "resolved"


class BlogPostOrigin(StrEnum):
    """Provenance of a blog post row.

    Distinguishes a hand-authored standalone blog post from one derived from a
    carousel project's embedded blog body. Existing standalone rows backfill to
    ``STANDALONE``; project-linked rows backfill to ``CAROUSEL``.
    """

    STANDALONE = "standalone"
    CAROUSEL = "carousel"


BLOG_POST_HARD_DELETABLE_ORIGINS: frozenset[BlogPostOrigin] = frozenset({
    BlogPostOrigin.STANDALONE
})
BLOG_POST_LINK_GUARDED_ORIGINS: frozenset[BlogPostOrigin] = frozenset({
    BlogPostOrigin.CAROUSEL
})

ERR_CAROUSEL_ORIGIN_DELETE_BLOCKED = "carousel_origin_delete_blocked"
ERR_BLOG_POST_SLUG_CONFLICT = "blog_post_slug_conflict"


FORBIDDEN_PHRASE_IN_TODAYS_WORLD = "In today's world"
FORBIDDEN_PHRASE_LETS_DIVE_IN = "Let's dive in"

DEFAULT_FORBIDDEN_PHRASES = [
    FORBIDDEN_PHRASE_IN_TODAYS_WORLD,
    FORBIDDEN_PHRASE_LETS_DIVE_IN,
]

__all__ = [
    "DEFAULT_FORBIDDEN_PHRASES",
    "FORBIDDEN_PHRASE_IN_TODAYS_WORLD",
    "FORBIDDEN_PHRASE_LETS_DIVE_IN",
    "BlogPostOrigin",
    "BlogPostStatus",
    "EditorialCommentStatus",
]
