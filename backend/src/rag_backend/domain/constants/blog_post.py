"""Domain-level constants for blog post management."""

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
    """Provenance of a blog post row (AE-0127).

    Distinguishes a hand-authored standalone blog post from one derived from a
    carousel project's embedded blog body. Existing standalone rows backfill to
    ``STANDALONE``; project-linked rows backfill to ``CAROUSEL``.
    """

    STANDALONE = "standalone"
    CAROUSEL = "carousel"


# Hard-delete policy per origin (AE-0296). Every ``BlogPostOrigin`` member MUST
# appear in exactly one of these sets — a unit test enforces completeness so a
# new origin cannot ship without an explicit delete policy.
BLOG_POST_HARD_DELETABLE_ORIGINS: frozenset[BlogPostOrigin] = frozenset(
    {BlogPostOrigin.STANDALONE}
)
# Origins whose rows back another public surface while linked to a project:
# hard delete is blocked (409) while ``project_id`` is set, because deleting
# the row would 404 the public carousel blog projection (ADR-0011). Once the
# parent project is deleted (``project_id`` → NULL), the detached row becomes
# hard-deletable like a standalone one.
BLOG_POST_LINK_GUARDED_ORIGINS: frozenset[BlogPostOrigin] = frozenset(
    {BlogPostOrigin.CAROUSEL}
)

ERR_CAROUSEL_ORIGIN_DELETE_BLOCKED = "carousel_origin_delete_blocked"


# Default forbidden phrases for persona training
FORBIDDEN_PHRASE_IN_TODAYS_WORLD = "In today's world"
FORBIDDEN_PHRASE_LETS_DIVE_IN = "Let's dive in"

# Common default forbidden phrases
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
