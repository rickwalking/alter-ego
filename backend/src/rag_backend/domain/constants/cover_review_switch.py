"""Constants for changing slide 1 of a completed carousel.

A cover the owner generates from the website ("Gerar capa com Grok") on a
completed carousel that still waits for its first approval becomes slide 1:
the slides are rendered again and the carousel stays in final review. A
carousel that is approved (scheduled ones included) or published is never
switched, by the picker or by a generation, because its slide 1 would change
without a new approval. A switch whose render failed, or that an approval
overtook, is rolled back (``rolled_back``).
"""

from __future__ import annotations

ERR_COVER_SWITCH_REQUIRES_REVIEW = "cover_switch_requires_review"

REASON_AUTO_SELECT_APPROVED = "carousel_approved"
REASON_AUTO_SELECT_PUBLISHED = "carousel_published"
REASON_AUTO_SELECT_NOT_IN_REVIEW = "not_in_final_review"

REASON_AUTO_SELECT_ROLLED_BACK = "rolled_back"

LOG_COVER_REVIEW_ROLLED_BACK = "cover_review_rolled_back"
LOG_COVER_REVIEW_ROLLBACK_FAILED = "cover_review_rollback_failed"

__all__ = [
    "ERR_COVER_SWITCH_REQUIRES_REVIEW",
    "LOG_COVER_REVIEW_ROLLBACK_FAILED",
    "LOG_COVER_REVIEW_ROLLED_BACK",
    "REASON_AUTO_SELECT_APPROVED",
    "REASON_AUTO_SELECT_NOT_IN_REVIEW",
    "REASON_AUTO_SELECT_PUBLISHED",
    "REASON_AUTO_SELECT_ROLLED_BACK",
]
