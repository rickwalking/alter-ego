"""The owner's Retry on a failed, blocked, escalated or rejected carousel.

``POST`` accepts one Retry at ``expected_version`` (202) or refuses it with a
typed code and no change (403 for ``not_owner`` / ``not_assigned_reviewer``,
404 when the carousel is missing, 409 otherwise). ``GET`` returns the
capability without writing anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import get_carousel_project_for_user
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser, UserModel
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.editorial_workflow_routes_support import (
    build_editorial_workflow_service,
)
from rag_backend.api.schemas.carousel_retry import (
    CarouselRetryAcceptedResponse,
    CarouselRetryCapabilityResponse,
    CarouselRetryRequest,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.modules.generation_queue.retry_public import (
    OwnerRetryCommand,
    OwnerRetryService,
    RetryCapability,
    RetryRefusal,
    RetryResult,
    RetrySurface,
    build_owner_retry,
)

router = APIRouter(tags=["carousel_owner_retry"])

_RETRY_PATH = "/carousels/{project_id}/workflow/retry"
_FORBIDDEN = frozenset({RetryRefusal.NOT_OWNER, RetryRefusal.NOT_ASSIGNED_REVIEWER})


@dataclass(frozen=True, kw_only=True)
class _Caller:
    db: AsyncSession
    user: UserModel


@dataclass(frozen=True, kw_only=True)
class _RetryContext:
    caller: _Caller
    project_id: UUID
    service: OwnerRetryService


def _caller(db: Annotated[AsyncSession, Depends(get_db)], user: EditorUser) -> _Caller:
    return _Caller(db=db, user=user)


def _context(
    request: Request,
    project_id: UUID,
    caller: Annotated[_Caller, Depends(_caller)],
) -> _RetryContext:
    engine = build_editorial_workflow_service(request)
    return _RetryContext(
        caller=caller,
        project_id=project_id,
        service=build_owner_retry(caller.db, engine),
    )


RetryContext = Annotated[_RetryContext, Depends(_context)]


@router.post(
    _RETRY_PATH,
    response_model=CarouselRetryAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def retry_carousel(
    request: Request, body: CarouselRetryRequest, context: RetryContext
) -> JSONResponse:
    """Retry the carousel's failed, blocked or rejected phase."""
    del request
    denied = await _access_denied(context)
    if denied is not None:
        return denied
    result = await context.service.retry(
        _command(context, expected_version=body.expected_version)
    )
    return _response(result)


@router.get(_RETRY_PATH, response_model=CarouselRetryCapabilityResponse)
async def get_retry_capability(context: RetryContext) -> JSONResponse:
    """Whether the carousel can be retried now, and as which kind."""
    denied = await _access_denied(context)
    if denied is not None:
        return denied
    capability = await context.service.inspect(_command(context))
    return JSONResponse(content=_capability(capability).model_dump())


async def _access_denied(context: _RetryContext) -> JSONResponse | None:
    caller = context.caller
    try:
        await get_carousel_project_for_user(caller.db, context.project_id, caller.user)
    except HTTPException as exc:
        return _error(exc.status_code, str(exc.detail))
    return None


def _command(
    context: _RetryContext, *, expected_version: int | None = None
) -> OwnerRetryCommand:
    return OwnerRetryCommand(
        project_id=str(context.project_id),
        actor_id=str(context.caller.user.id),
        surface=RetrySurface.WEB,
        expected_version=expected_version,
    )


def _error(code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={"detail": detail})


def _response(result: RetryResult) -> JSONResponse:
    if result.refusal is not None or result.kind is None:
        return _refused(result.refusal or RetryRefusal.CONCURRENT_UPDATE)
    payload = CarouselRetryAcceptedResponse(
        accepted=True,
        retry_kind=result.kind.value,
        current_phase=result.phase,
        phase_status=result.phase_status,
        lock_version=result.lock_version,
        autopilot_run_id=(
            str(result.autopilot_run_id) if result.autopilot_run_id else None
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED, content=payload.model_dump()
    )


def _refused(refusal: RetryRefusal) -> JSONResponse:
    if refusal is RetryRefusal.NOT_FOUND:
        return _error(status.HTTP_404_NOT_FOUND, refusal.value)
    if refusal in _FORBIDDEN:
        return _error(status.HTTP_403_FORBIDDEN, refusal.value)
    return _error(status.HTTP_409_CONFLICT, refusal.value)


def _capability(capability: RetryCapability) -> CarouselRetryCapabilityResponse:
    return CarouselRetryCapabilityResponse(
        can_retry=capability.can_retry,
        retry_kind=capability.kind.value if capability.kind else None,
        refusal_code=capability.refusal.value if capability.refusal else None,
        lock_version=capability.lock_version,
    )


__all__ = ["router"]
