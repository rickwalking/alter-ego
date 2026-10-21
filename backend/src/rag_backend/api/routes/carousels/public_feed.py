"""Public projection of the carousel list (the anonymous gallery feed)."""

from __future__ import annotations

from typing import Final

from rag_backend.api.schemas import CarouselProjectResponse
from rag_backend.domain.models import CarouselProject, CarouselStatus, User

PUBLIC_FEED_STATUS: Final = CarouselStatus.COMPLETED

PUBLIC_FEED_REDACTED: Final[dict[str, object]] = {
    "blog_markdown": None,
    "blog_translations": None,
    "caption": None,
    "linkedin_post_pt": None,
    "linkedin_post_en": None,
    "error_message": None,
    "output_dir": None,
    "pdf_path": None,
    "pdf_path_en": None,
    "custom_visual_details": None,
    "pov_thesis": None,
    "pov_personal_proof": None,
    "hook_asset_id": None,
    "persona_id": None,
    "research_sources": [],
}


def is_public_feed_view(user: User | None, public_only: bool | None) -> bool:
    """True when the list is served as the public feed (anonymous or non-admin public).

    An admin keeps the full project even with ``public=true``; everyone else
    browsing public carousels gets the redacted card fields only.
    """
    if user is None:
        return True
    return public_only is True and not user.is_admin()


def public_feed_status(
    user: User | None, requested: CarouselStatus | None
) -> CarouselStatus | None:
    """Anonymous visitors only ever see finished carousels, like the public viewer.

    A public carousel that is still generating (or failed) is not part of the
    gallery; the viewer already answers 404 for it.
    """
    if user is not None:
        return requested
    return PUBLIC_FEED_STATUS


def public_feed_item(project: CarouselProject) -> CarouselProjectResponse:
    """The list item without owner-only drafts, briefs, paths or errors."""
    full = CarouselProjectResponse.model_validate(project)
    return full.model_copy(update=PUBLIC_FEED_REDACTED)
