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
    "rubric_id": None,
    "research_sources": [],
    "slides": [],
}


def is_public_feed_view(user: User | None, *, public_only: bool | None) -> bool:
    """True when the list is served as the public feed (anonymous or non-admin public).

    An admin keeps the full project even with ``public=true``; everyone else
    browsing public carousels gets the redacted card fields only.
    """
    if user is None:
        return True
    return public_only is True and not user.is_admin()


def public_feed_status(
    requested: CarouselStatus | None, *, public_view: bool
) -> CarouselStatus | None:
    """The public feed only ever lists finished carousels, like the public viewer.

    A public carousel that is still generating (or failed) is not part of the
    gallery; the viewer already answers 404 for it. Admins and owners keep the
    status they asked for.
    """
    if public_view:
        return PUBLIC_FEED_STATUS
    return requested


def public_feed_item(project: CarouselProject) -> CarouselProjectResponse:
    """The list item without owner-only drafts, briefs, paths or errors.

    Slides are dropped too: their ``image_path`` is a server path under the
    output directory, and the gallery card reads its images from the design
    tokens.
    """
    full = CarouselProjectResponse.model_validate(project)
    return full.model_copy(update=PUBLIC_FEED_REDACTED)
