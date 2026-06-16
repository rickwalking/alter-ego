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
