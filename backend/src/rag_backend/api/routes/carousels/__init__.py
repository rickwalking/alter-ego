from fastapi import APIRouter

from .admin import router as admin_router
from .crud import router as crud_router
from .editorial_workflow import router as editorial_workflow_router
from .generation import router as generation_router
from .media import router as media_router
from .publishing import router as publishing_router

PREFIX = "/carousels"

router = APIRouter(tags=["carousels"])
router.include_router(admin_router, prefix="")
router.include_router(crud_router, prefix=PREFIX)
router.include_router(generation_router, prefix=PREFIX)
router.include_router(media_router, prefix=PREFIX)
router.include_router(publishing_router, prefix=PREFIX)
router.include_router(editorial_workflow_router, prefix="")

# Explicit re-exports for convenience
from .crud import create_carousel  # noqa: E402
from .generation import generate_carousel  # noqa: E402
from .media import get_carousel_blog, get_carousel_image, get_carousel_pdf  # noqa: E402
from .publishing import generate_caption  # noqa: E402
