"""Aggregated carousel API router."""

from fastapi import APIRouter

from .admin import router as admin_router
from .crud import router as crud_router
from .editorial_workflow import router as editorial_workflow_router
from .media import router as media_router
from .preview import router as preview_router
from .publishing import router as publishing_router

PREFIX = "/carousels"

router = APIRouter(tags=["carousels"])
router.include_router(admin_router, prefix="")
router.include_router(crud_router, prefix=PREFIX)
router.include_router(media_router, prefix=PREFIX)
router.include_router(preview_router, prefix=PREFIX)
router.include_router(publishing_router, prefix=PREFIX)
router.include_router(editorial_workflow_router, prefix="")

__all__ = ["PREFIX", "router"]
