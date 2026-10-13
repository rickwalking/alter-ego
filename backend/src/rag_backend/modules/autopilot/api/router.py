"""Autopilot HTTP routes.

Every route on this router requires the service API key. Decorate each
route with the shared slowapi limit (``RATE_LIMIT_AUTOPILOT`` /
``RATE_LIMIT_SCOPE_AUTOPILOT``) so they share one 10/minute budget per IP.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Request, status

from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.bootstrap import default_signals_service
from rag_backend.modules.autopilot.constants import (
    APP_STATE_SIGNALS,
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    PATH_SIGNALS,
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.ports import SignalsReader
from rag_backend.modules.autopilot.domain.signals import SignalsBundle

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@router.get(
    PATH_SIGNALS,
    response_model=SignalsBundle,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_API_KEY_INVALID},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": DETAIL_API_KEY_UNCONFIGURED,
        },
    },
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_autopilot_signals(request: Request) -> SignalsBundle:
    """Return the deduped signal bundle for the scout."""
    reader = signals_reader(request)
    return await reader.collect_all()


def signals_reader(request: Request) -> SignalsReader:
    """Prefer an app-state override, otherwise the process service."""
    override: object = getattr(request.app.state, APP_STATE_SIGNALS, None)
    if override is None:
        return default_signals_service()
    return cast(SignalsReader, override)
