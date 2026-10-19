"""Approval is invalidated by edits (AE-0424, ADR-0025).

A content edit while a post is ``under_review`` or ``approved`` (scheduled or
not) returns it to ``draft`` and clears the schedule and review stamps, so a
review never approves unseen content and the due-post sweep (which publishes
only ``approved`` rows) skips the edited post. A published post stays
published on edit (state diagram: ``published --> published``).
"""

from __future__ import annotations

from rag_backend.domain.constants.blog_post import BlogPostStatus

REVIEW_RESET_STATUSES = frozenset({
    BlogPostStatus.UNDER_REVIEW.value,
    BlogPostStatus.APPROVED.value,
})
CONTENT_EDIT_FIELDS = frozenset({"content", "title", "excerpt"})


def review_reset_values(
    status: str | None, values: dict[str, object]
) -> dict[str, object]:
    """Extra column values for a write: the draft reset, or ``{}``."""
    if status not in REVIEW_RESET_STATUSES:
        return {}
    if not CONTENT_EDIT_FIELDS.intersection(values):
        return {}
    return {
        "status": BlogPostStatus.DRAFT.value,
        "scheduled_publish_at": None,
        "submitted_for_review_at": None,
        "approved_at": None,
    }


__all__ = ["CONTENT_EDIT_FIELDS", "review_reset_values"]
