"""Autopilot HTTP routes.

Every route on this router requires the service API key. Decorate each
route with the shared slowapi limit (``RATE_LIMIT_AUTOPILOT`` /
``RATE_LIMIT_SCOPE_AUTOPILOT``) so they share one 10/minute budget per IP.
The signals body is filled by AE-0352; this handler only proves the route
is mounted and authenticated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.constants import (
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    PATH_SIGNALS,
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@router.get(
    PATH_SIGNALS,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_autopilot_signals(request: Request) -> JSONResponse:
    """Return 200 once the scout key is accepted.

    AE-0352 replaces this body with the signal bundle. ``request`` stays in
    the signature so slowapi can read the caller address; the body does not
    use it.
    """
    del request
    return JSONResponse(status_code=status.HTTP_200_OK, content={})
