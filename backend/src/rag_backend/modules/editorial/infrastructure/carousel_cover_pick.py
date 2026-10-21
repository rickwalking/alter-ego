"""The publish-step slide-1 cover picker, wired over the session.

``EditorialCoverLibrary`` reads the owner's slide-1 photos (role ``hook``,
stored file present) and stages one where a project's slides render;
``cover_pick_service`` builds the picker over it, the given GrokBot offer
source, and the cover switch (lock-version CAS + republish).

The ORM, repositories and the carousel services are imported lazily (the
editorial facade loads while the ORM registry is still initialising).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_ROLE_HOOK
from rag_backend.domain.models.carousel_creator_asset import (
    CarouselCreatorAsset,
    CreatorAssetLibraryQuery,
)
from rag_backend.modules.editorial.domain.models import CarouselProject
from rag_backend.modules.editorial.infrastructure.carousel_cover import (
    slide_cover_switch_service,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import (
    creator_asset_service,
    creator_assets,
    project_output_root,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.cover_pick import (
        CoverOfferSource,
        CoverPickService,
    )


class EditorialCoverLibrary:
    """``CoverLibrary`` over the creator-asset rows and files of one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def photos(self, owner_id: str) -> tuple[CarouselCreatorAsset, ...]:
        """The owner's ``hook`` photos, newest first, whose file exists."""
        library = await creator_assets(self._session).list_for_owner(
            CreatorAssetLibraryQuery(owner_id=owner_id, role=CREATOR_ASSET_ROLE_HOOK)
        )
        service = creator_asset_service(self._session)
        return tuple(asset for asset in library if service.has_stored_file(asset))

    async def stage(
        self, project: CarouselProject, asset: CarouselCreatorAsset
    ) -> None:
        """Copy the photo where the project's slides render."""
        from rag_backend.application.services.carousel.creator_asset_service import (
            StageCreatorAssetCommand,
        )

        creator_asset_service(self._session).stage_into_candidate_artifact(
            StageCreatorAssetCommand(
                asset=asset, staging_root=project_output_root(project)
            )
        )


def cover_pick_service(
    session: AsyncSession, offers: CoverOfferSource
) -> CoverPickService:
    """The picker of one session over ``offers`` (the autopilot's GrokBot cover)."""
    from rag_backend.application.services.carousel.cover_pick import (
        CoverPickDeps,
        CoverPickService,
    )

    return CoverPickService(
        CoverPickDeps(
            library=EditorialCoverLibrary(session),
            offers=offers,
            switcher=slide_cover_switch_service(session),
        )
    )


__all__ = ["EditorialCoverLibrary", "cover_pick_service"]
