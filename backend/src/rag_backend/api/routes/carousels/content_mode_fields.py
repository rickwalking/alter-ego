"""Map the create request's content-mode fields onto the project (AE-0373)."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from rag_backend.api.schemas.carousel_content_mode import ContentModeRequestFields


class ProjectContentModeKwargs(TypedDict):
    """``CarouselProject`` keyword arguments for the content mode."""

    content_mode: str
    pov_thesis: str | None
    pov_personal_proof: str | None
    pov_format: str | None
    slide_count: int | None
    cta_goal: str
    hook_asset_id: UUID | None


def content_mode_fields(request: ContentModeRequestFields) -> ProjectContentModeKwargs:
    """The stored values: defaults applied, Radar IA when the mode is omitted."""
    return ProjectContentModeKwargs(
        content_mode=request.resolved_mode,
        pov_thesis=request.pov_thesis,
        pov_personal_proof=request.pov_personal_proof,
        pov_format=request.resolved_pov_format(),
        slide_count=request.resolved_slide_count(),
        cta_goal=request.resolved_cta_goal(),
        hook_asset_id=request.hook_asset_id,
    )


__all__ = ["ProjectContentModeKwargs", "content_mode_fields"]
