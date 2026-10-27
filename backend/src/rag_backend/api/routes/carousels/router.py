"""Aggregated carousel API router.

The creator-asset library and cover-prompt-ideas routers are included before CRUD so
"/creator-assets" and "/cover-prompt-ideas" are not read as "/{project_id}".
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .archive import router as archive_router
from .copy_edit import router as copy_edit_router
from .copy_versions import router as copy_versions_router
from .cover_generate import router as cover_generate_router
from .cover_pick import router as cover_pick_router
from .cover_prompt_ideas import router as cover_prompt_ideas_router
from .creator_asset_library import router as creator_asset_library_router
from .creator_assets import router as creator_assets_router
from .crud import router as crud_router
from .editorial_workflow import router as editorial_workflow_router
from .generation_log import router as generation_log_router
from .hook import router as hook_router
from .media import router as media_router
from .preview import router as preview_router
from .public_view import router as public_view_router
from .publishing import router as publishing_router
from .repair import router as repair_router
from .republish import router as republish_router
from .slide_edit import router as slide_edit_router
from .story_image import router as story_image_router
from .strategies import router as strategies_router

PREFIX = "/carousels"

router = APIRouter(tags=["carousels"])
router.include_router(admin_router, prefix="")
router.include_router(strategies_router, prefix=PREFIX)
router.include_router(creator_asset_library_router, prefix=PREFIX)
router.include_router(cover_prompt_ideas_router, prefix=PREFIX)
router.include_router(crud_router, prefix=PREFIX)
router.include_router(creator_assets_router, prefix=PREFIX)
router.include_router(copy_edit_router, prefix=PREFIX)
router.include_router(copy_versions_router, prefix=PREFIX)
router.include_router(generation_log_router, prefix=PREFIX)
router.include_router(archive_router, prefix=PREFIX)
router.include_router(cover_pick_router, prefix=PREFIX)
router.include_router(cover_generate_router, prefix=PREFIX)
router.include_router(hook_router, prefix=PREFIX)
router.include_router(media_router, prefix=PREFIX)
router.include_router(public_view_router, prefix=PREFIX)
router.include_router(preview_router, prefix=PREFIX)
router.include_router(publishing_router, prefix=PREFIX)
router.include_router(repair_router, prefix=PREFIX)
router.include_router(republish_router, prefix=PREFIX)
router.include_router(slide_edit_router, prefix=PREFIX)
router.include_router(story_image_router, prefix=PREFIX)
router.include_router(editorial_workflow_router, prefix="")

__all__ = ["PREFIX", "router"]
