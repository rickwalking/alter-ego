"""Release-state value object for the publishing bounded context.

Publishing distinguishes a content item's *release lifecycle* — where it sits on
the path from draft to publicly released — from the upstream editorial *approval*
(``approved_for_publish``, owned by the editorial context, AE-0111) and from raw
visibility flags. AE-0111 already split approval ``!=`` release on the editorial
side; this module owns the *publishing* read of that release lifecycle.

:class:`ReleaseState` is derived **directly** from the canonical blog workflow
status language (:class:`~rag_backend.domain.constants.blog_post.BlogPostStatus`)
— it introduces no new domain strings (AE-0126 constraint). It maps each blog
status to a coarse release phase the publishing/distribution paths key off,
without changing who-can-see-what or who writes the status.

Behavior-preserving + additive (AE-0126): this is a read projection only. The
auto-publish behavior cutover is DEFERRED (documented follow-up); the existing
publish routes stay the sole writer of the status.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rag_backend.domain.constants.blog_post import BlogPostStatus


class ReleasePhase(StrEnum):
    """Coarse release lifecycle phase derived from the blog workflow status.

    A publishing-side projection over :class:`BlogPostStatus` — NOT a new status
    language. Each value names where a content item sits on the draft → released
    path so the distribution/calendar/board reads can key off a stable phase
    without coupling to every individual blog status string.
    """

    UNPUBLISHED = "unpublished"
    IN_REVIEW = "in_review"
    READY = "ready"
    RELEASED = "released"
    RETIRED = "retired"


# Mapping from the canonical blog status to the coarse release phase. The keys
# are the canonical :class:`BlogPostStatus` members (object-identity), so no new
# status strings are introduced; the values are this module's coarse phases.
_STATUS_TO_PHASE: dict[BlogPostStatus, ReleasePhase] = {
    BlogPostStatus.DRAFT: ReleasePhase.UNPUBLISHED,
    BlogPostStatus.UNDER_REVIEW: ReleasePhase.IN_REVIEW,
    BlogPostStatus.APPROVED: ReleasePhase.READY,
    BlogPostStatus.PUBLISHED: ReleasePhase.RELEASED,
    BlogPostStatus.ARCHIVED: ReleasePhase.RETIRED,
}


@dataclass(frozen=True)
class ReleaseState:
    """The publishing release-lifecycle state of a content item.

    Built from the item's canonical blog ``status``. ``is_released`` is the
    single source of truth for "this content has been publicly released"; it is
    independent of the upstream editorial approval state (AE-0111). The state is
    a read projection and never mutates the underlying status.
    """

    status: BlogPostStatus

    @property
    def phase(self) -> ReleasePhase:
        """The coarse release phase derived from the blog status."""
        return _STATUS_TO_PHASE[self.status]

    @property
    def is_released(self) -> bool:
        """``True`` iff the content item has been publicly released."""
        return self.phase is ReleasePhase.RELEASED

    @classmethod
    def from_status(cls, status: str | None) -> ReleaseState:
        """Build the release state from a (possibly absent) blog status string.

        Falls back to :attr:`BlogPostStatus.DRAFT` (``unpublished``) when the
        status is missing or unrecognized, so callers always get a well-defined
        phase without raising.
        """
        if status is None:
            return cls(status=BlogPostStatus.DRAFT)
        try:
            return cls(status=BlogPostStatus(status))
        except ValueError:
            return cls(status=BlogPostStatus.DRAFT)


__all__ = [
    "ReleasePhase",
    "ReleaseState",
]
