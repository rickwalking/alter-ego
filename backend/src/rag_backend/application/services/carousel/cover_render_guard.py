"""No render puts an unreviewed slide-1 cover on an approved or public carousel.

Every artifact build records the cover it rendered slide 1 with
(``slide_one_cover`` in the artifact manifest: the ``slide_cover`` asset id,
else the bound slide-1 photo, else empty). Before any re-render of a carousel
that is approved for publishing or released (the republish service, the
republish sweep, a slide-text edit's republish, a manual republish, the cover
switch), the finalize step compares the cover the carousel would render now
with the one the active artifact version recorded; a different cover is
refused (``cover_change_requires_review``) and nothing is re-rendered. The
completed carousel keeps its artifacts.

An active version built before the manifest recorded the cover has no record;
there is no other stored trace of the cover a render used, so such a version
is not compared (the cover switch itself never writes to an approved or public
carousel, and approval is refused while a switch's render is pending).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import (
    ReviewState,
    cover_switch_refusal,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_CHANGE_REQUIRES_REVIEW,
)
from rag_backend.domain.models import CarouselProject


def cover_identity(project: CarouselProject) -> str:
    """The cover slide 1 renders with now: the cover asset, else the photo, else empty."""
    if project.slide_cover is not None:
        return str(project.slide_cover.asset_id)
    if project.hook_asset_id is not None:
        return str(project.hook_asset_id)
    return ""


def recorded_cover(project: CarouselProject) -> str | None:
    """The cover the active artifact version recorded; None without a record."""
    from pydantic import ValidationError

    from rag_backend.application.services.carousel.artifact_manifest import (
        CarouselArtifactManifestPayload,
    )
    from rag_backend.application.services.carousel.artifact_path_resolver import (
        resolve_manifest_path,
    )

    path = resolve_manifest_path(project)
    if path is None or not path.is_file():
        return None
    try:
        payload = CarouselArtifactManifestPayload.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError):
        return None
    return payload.slide_one_cover


async def unreviewed_cover_refusal(
    db: AsyncSession, project: CarouselProject
) -> str | None:
    """``cover_change_requires_review`` when this render would change slide 1's
    cover on an approved or public carousel; None otherwise."""
    state = await _review_state(db, str(project.id))
    if state is None or cover_switch_refusal(state) is None:
        return None
    recorded = recorded_cover(project)
    if recorded is None or recorded == cover_identity(project):
        return None
    return ERR_COVER_CHANGE_REQUIRES_REVIEW


async def _review_state(db: AsyncSession, project_id: str) -> ReviewState | None:
    """The committed approval and release, through the editorial facade."""
    from rag_backend.modules.editorial.public import EditorialReviewState

    return await EditorialReviewState(db).review_state(project_id)


__all__ = ["cover_identity", "recorded_cover", "unreviewed_cover_refusal"]
