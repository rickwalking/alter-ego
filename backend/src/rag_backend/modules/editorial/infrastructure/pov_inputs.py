"""Persona and slide-1 photo lookups for unattended carousels (PR #106 review).

- ``resolve_persona_id``: the configured ``AUTOPILOT_PERSONA_ID`` when that
  persona exists, else the newest persona with the fallback name ("Pedro"),
  else None (the caller records it; a POV run then escalates unscored).
- ``hook_photo_id``: the owner's slide-1 photo, library role ``hook``: the one
  most recently used on a carousel, else the newest uploaded, skipping any
  photo whose stored file is gone (an unreadable photo counts as missing).
- ``stage_hook_photo``: copy the bound photo where the slides render, the same
  staging ``PUT /{project_id}/hook-photo`` does.

The ORM, repositories and the creator-asset service are imported lazily (the
editorial facade loads while the ORM registry is still initialising).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.creator_asset import CREATOR_ASSET_ROLE_HOOK
from rag_backend.domain.models.carousel_creator_asset import (
    CarouselCreatorAsset,
    CreatorAssetLibraryQuery,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.editorial.domain.models import CarouselProject

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.creator_asset_service import (
        CreatorAssetService,
    )
    from rag_backend.infrastructure.database.creator_asset_repository import (
        PostgresCreatorAssetRepository,
    )

_RECENT_PROJECTS = 20


class PovInputsAcl:
    """Session-scoped persona and creator-photo reads for the autopilot."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_persona(self, persona_id: str | None) -> PersonaProfile | None:
        """The persona entity, or None when the id is empty or unknown."""
        if not persona_id:
            return None
        from rag_backend.infrastructure.database.models.persona_rubric import (
            PersonaProfileModel,
        )

        model = await self._session.get(PersonaProfileModel, persona_id)
        return model.to_entity() if model is not None else None

    async def project_persona(self, project_id: str) -> PersonaProfile | None:
        """AE-0397: the persona the project was created with, for its resumes."""
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        project = await self._session.get(CarouselProjectModel, project_id)
        persona_id = project.persona_id if project is not None else None
        return await self.load_persona(str(persona_id) if persona_id else None)

    async def resolve_persona_id(self, configured: str, name: str) -> str | None:
        """The configured persona when it exists, else the newest named ``name``."""
        if configured and await self.load_persona(configured) is not None:
            return configured
        from rag_backend.infrastructure.database.models.persona_rubric import (
            PersonaProfileModel,
        )

        result = await self._session.execute(
            select(PersonaProfileModel.id)
            .where(func.lower(PersonaProfileModel.name) == name.strip().lower())
            .order_by(PersonaProfileModel.updated_at.desc())
            .limit(1)
        )
        found = result.scalar_one_or_none()
        return str(found) if found is not None else None

    async def hook_photo_id(self, owner_id: str) -> str | None:
        """The owner's next slide-1 photo (AE-0395 rotation).

        A photo never used on a carousel comes first (newest first), then the
        used ones from the least recently used, so consecutive POV carousels
        never repeat a photo while the library has another one.
        """
        if not owner_id:
            return None
        service = creator_asset_service(self._session)
        for asset in await self._candidates(owner_id):
            if service.has_stored_file(asset):
                return str(asset.id)
        return None

    async def stage_hook_photo(self, project: CarouselProject) -> None:
        """Copy the project's bound slide-1 photo where its slides render."""
        if project.hook_asset_id is None:
            return
        from rag_backend.application.services.carousel.creator_asset_service import (
            StageCreatorAssetCommand,
        )

        asset = await creator_assets(self._session).get_by_id(project.hook_asset_id)
        if asset is None:
            return
        creator_asset_service(self._session).stage_into_candidate_artifact(
            StageCreatorAssetCommand(
                asset=asset, staging_root=project_output_root(project)
            )
        )

    async def _candidates(self, owner_id: str) -> list[CarouselCreatorAsset]:
        library = await creator_assets(self._session).list_for_owner(
            CreatorAssetLibraryQuery(owner_id=owner_id, role=CREATOR_ASSET_ROLE_HOOK)
        )
        by_id = {str(asset.id): asset for asset in library}
        recent = await self._recently_used(owner_id)
        used = list(dict.fromkeys(key for key in recent if key in by_id))
        never_used = [key for key in by_id if key not in used]
        ordered = [*never_used, *reversed(used)]
        return [by_id[key] for key in ordered]

    async def _recently_used(self, owner_id: str) -> list[str]:
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        result = await self._session.execute(
            select(CarouselProjectModel.hook_asset_id)
            .where(
                CarouselProjectModel.owner_id == owner_id,
                CarouselProjectModel.hook_asset_id.is_not(None),
            )
            .order_by(CarouselProjectModel.updated_at.desc())
            .limit(_RECENT_PROJECTS)
        )
        return [str(value) for value in result.scalars().all() if value is not None]


def creator_assets(session: AsyncSession) -> PostgresCreatorAssetRepository:
    from rag_backend.infrastructure.database.creator_asset_repository import (
        PostgresCreatorAssetRepository,
    )

    return PostgresCreatorAssetRepository(session)


def creator_asset_service(session: AsyncSession) -> CreatorAssetService:
    from rag_backend.application.services.carousel.creator_asset_service import (
        CreatorAssetService,
    )
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    return CreatorAssetService(
        asset_repo=creator_assets(session),
        carousel_repo=PostgresCarouselRepository(session),
        assets_root=Path(get_settings().carousel_creator_assets_dir),
    )


def project_output_root(project: CarouselProject) -> Path:
    """Where the slides render: the output dir, else the default one."""
    from rag_backend.infrastructure.config.settings import get_settings

    if project.output_dir:
        return Path(project.output_dir).resolve()
    return (Path(get_settings().carousel_output_dir) / str(project.id)).resolve()


def as_uuid(value: str | None) -> UUID | None:
    """A stored id string as a UUID (None stays None)."""
    return UUID(value) if value else None


__all__ = [
    "PovInputsAcl",
    "as_uuid",
    "creator_asset_service",
    "creator_assets",
    "project_output_root",
]
