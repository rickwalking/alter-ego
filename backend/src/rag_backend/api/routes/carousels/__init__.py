from fastapi import APIRouter

from .crud import router as crud_router
from .generation import router as generation_router
from .media import router as media_router
from .publishing import router as publishing_router

PREFIX = "/carousels"

router = APIRouter(tags=["carousels"])
router.include_router(crud_router, prefix=PREFIX)
router.include_router(generation_router, prefix=PREFIX)
router.include_router(media_router, prefix=PREFIX)
router.include_router(publishing_router, prefix=PREFIX)

from .crud import *  # noqa: E402, F403
from .deps import *  # noqa: E402, F403
from .generation import *  # noqa: E402, F403
from .helpers import *  # noqa: E402, F403
from .media import *  # noqa: E402, F403
from .publishing import *  # noqa: E402, F403
