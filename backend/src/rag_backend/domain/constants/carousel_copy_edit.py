"""Constants for saving a carousel's Instagram caption and LinkedIn posts.

The publish page saves the caption and the PT/EN LinkedIn posts through
``PATCH /api/carousels/{id}/copy`` guarded by the carousel ``lock_version``
(``If-Match``). The caption of a carousel already published on Instagram is
read-only. An Instagram publish sends the saved caption, never text the page
has not saved. The limits are the platforms' own: Instagram rejects a caption over
2,200 characters, LinkedIn a post over 3,000.
"""

from __future__ import annotations

from typing import Final

INSTAGRAM_CAPTION_MAX_CHARS: Final = 2200
LINKEDIN_POST_MAX_CHARS: Final = 3000

ERR_CAPTION_PUBLISHED: Final = "caption_published"
ERR_CAPTION_NOT_SAVED: Final = "caption_not_saved"
ERR_CAPTION_MISSING: Final = "caption_missing"
ERR_COPY_EDIT_EMPTY: Final = (
    "at least one of caption, linkedin_post_pt or linkedin_post_en is required"
)

LOG_EVENT_COPY_SAVED: Final = "carousel_copy_saved"

__all__ = [
    "ERR_CAPTION_MISSING",
    "ERR_CAPTION_NOT_SAVED",
    "ERR_CAPTION_PUBLISHED",
    "ERR_COPY_EDIT_EMPTY",
    "INSTAGRAM_CAPTION_MAX_CHARS",
    "LINKEDIN_POST_MAX_CHARS",
    "LOG_EVENT_COPY_SAVED",
]
