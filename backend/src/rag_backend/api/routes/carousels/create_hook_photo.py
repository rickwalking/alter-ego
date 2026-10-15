"""The slide-1 photo chosen at create time (PR #106 review, item 4).

A POV create request names ``hook_asset_id`` (the schema makes it a 422 when
missing). ``check_hook_photo`` runs BEFORE the project is inserted, so an
unknown, foreign or unreadable photo never leaves a POV project without its
photo; ``bind_hook_photo`` then binds and stages it exactly like
``PUT /{project_id}/hook-photo``.
"""

from __future__ import annotations

from rag_backend.api.schemas import CarouselProjectCreate
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetService,
    HookPhotoCommand,
)
from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetValidationError,
)
from rag_backend.domain.models import CarouselProject, User

from .creator_assets import default_output_root, map_validation_error


async def check_hook_photo(
    service: CreatorAssetService, user: User, request: CarouselProjectCreate
) -> None:
    """The photo exists, is the caller's (or an admin's call) and is readable."""
    if request.hook_asset_id is None:
        return
    try:
        await service.library_image_path(user, request.hook_asset_id)
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error


async def bind_hook_photo(
    service: CreatorAssetService, project: CarouselProject, user: User
) -> CarouselProject:
    """Bind ``project.hook_asset_id`` and stage the file where slides render."""
    if project.hook_asset_id is None:
        return project
    try:
        return await service.select_hook_photo(
            HookPhotoCommand(
                project=project,
                user=user,
                creator_asset_id=project.hook_asset_id,
                output_root=default_output_root(project),
            )
        )
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error


__all__ = ["bind_hook_photo", "check_hook_photo"]
