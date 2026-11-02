"""Constants for changing slide 1 of a completed carousel.

A cover the owner generates from the website ("Gerar capa com Grok") on a
completed carousel that still waits for its first approval becomes slide 1:
the slides are rendered again and the carousel stays in final review. A
carousel that is approved (scheduled ones included) or published is never
switched, by the picker or by a generation, because its slide 1 would change
without a new approval.
"""

from __future__ import annotations

ERR_COVER_SWITCH_REQUIRES_REVIEW = "cover_switch_requires_review"

REASON_AUTO_SELECT_APPROVED = "carousel_approved"
REASON_AUTO_SELECT_PUBLISHED = "carousel_published"
REASON_AUTO_SELECT_NOT_IN_REVIEW = "not_in_final_review"

LOG_COVER_REVIEW_RENDER_FAILED = "cover_review_render_failed"

__all__ = [
    "ERR_COVER_SWITCH_REQUIRES_REVIEW",
    "LOG_COVER_REVIEW_RENDER_FAILED",
    "REASON_AUTO_SELECT_APPROVED",
    "REASON_AUTO_SELECT_NOT_IN_REVIEW",
    "REASON_AUTO_SELECT_PUBLISHED",
]
