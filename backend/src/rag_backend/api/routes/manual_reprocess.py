"""Owner/admin manual carousel recovery endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from rag_backend.api.dependencies.carousel_access import get_carousel_project_for_user
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser, UserModel
from rag_backend.api.schemas.carousel_reprocess import (
    GenerationRunReprocessRequest,
    MaintenanceProcessResponse,
    ManualRecoveryCapabilityResponse,
    ManualReprocessRequest,
    ManualReprocessResponse,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.modules.generation_queue import (
    FullMaintenanceControl,
    MaintenanceEnqueue,
    WebMaintenanceGateway,
)
from rag_backend.modules.generation_queue.public import (
    MaintenanceNotifier,
    ManualRecoveryService,
    ManualReprocessCommand,
    RecoveryCapability,
    RecoveryOutcome,
    RecoveryResult,
    build_manual_recovery,
)

router = APIRouter(tags=["carousel_manual_recovery"])

_PROJECT_PATH = "/carousels/{project_id}/workflow/reprocess"
_RUN_PATH = "/generation-runs/{run_id}/reprocess"
_PROCESS_PATH = "/generation-runs/process"
_NOT_FOUND = "not_found"
_CONCURRENT_UPDATE = "concurrent_update"
_UNAVAILABLE = "maintenance_unavailable"


@dataclass(frozen=True)
class _RecoveryContext:
    db: AsyncSession
    user: UserModel
    service: ManualRecoveryService


def _context(request: Request, db: AsyncSession, user: UserModel) -> _RecoveryContext:
    notifier: MaintenanceNotifier | None = getattr(
        request.app.state, "manual_recovery_notifier", None
    )
    return _RecoveryContext(
        db=db, user=user, service=build_manual_recovery(db, notifier)
    )


def _editor_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: EditorUser,
) -> _RecoveryContext:
    return _context(request, db, user)


EditorContext = Annotated[_RecoveryContext, Depends(_editor_context)]


def _admin_required(user: UserModel) -> JSONResponse | None:
    if user.role == UserRole.ADMIN.value:
        return None
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Admin access required"},
    )


def _control(request: Request, db: AsyncSession) -> FullMaintenanceControl:
    override: FullMaintenanceControl | None = getattr(
        request.app.state, "maintenance_control", None
    )
    if override is not None:
        return override
    bind = db.bind
    engine = bind.engine if isinstance(bind, AsyncConnection) else bind
    return WebMaintenanceGateway(engine)


@router.post(
    _PROJECT_PATH,
    response_model=ManualReprocessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_carousel(
    project_id: UUID,
    body: ManualReprocessRequest,
    context: EditorContext,
) -> JSONResponse:
    """Queue or return manual recovery for an owned stuck carousel."""
    try:
        await get_carousel_project_for_user(context.db, project_id, context.user)
    except HTTPException as exc:
        return _http_error(exc)
    command = ManualReprocessCommand(
        project_id=str(project_id),
        run_id=body.run_id,
        actor_id=str(context.user.id),
        expected_version=body.expected_version,
    )
    return _response(await context.service.reprocess(command))


@router.get(_PROJECT_PATH, response_model=ManualRecoveryCapabilityResponse)
async def get_reprocess_capability(
    project_id: UUID, context: EditorContext
) -> ManualRecoveryCapabilityResponse:
    """Return workspace capability and safe current-run progress."""
    try:
        await get_carousel_project_for_user(context.db, project_id, context.user)
    except HTTPException as exc:
        return _http_error(exc)
    command = ManualReprocessCommand(
        project_id=str(project_id), run_id=None, actor_id=str(context.user.id)
    )
    return _capability(await context.service.inspect(command))


@router.post(
    _RUN_PATH,
    response_model=ManualReprocessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_generation_run(
    run_id: UUID,
    body: GenerationRunReprocessRequest,
    context: EditorContext,
) -> JSONResponse:
    """Queue or return admin recovery for an existing generation run."""
    denied = _admin_required(context.user)
    if denied is not None:
        return denied
    command = ManualReprocessCommand(
        project_id=None,
        run_id=run_id,
        actor_id=str(context.user.id),
        expected_version=body.expected_version,
    )
    return _response(await context.service.reprocess(command))


@router.post(
    _PROCESS_PATH,
    response_model=MaintenanceProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def process_generation_queue(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: EditorUser,
) -> JSONResponse:
    """Enqueue the same full maintenance control job used by cron."""
    denied = _admin_required(user)
    if denied is not None:
        return denied
    try:
        result = await _control(request, db).request_full()
    except Exception:
        return _unavailable_response()
    return _maintenance_response(result)


def _unavailable_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": _UNAVAILABLE},
    )


def _maintenance_response(result: MaintenanceEnqueue) -> JSONResponse:
    if result.job_id is None:
        return _unavailable_response()
    accepted = result.inserted
    payload = MaintenanceProcessResponse(
        outcome="queued" if accepted else "existing", job_id=result.job_id
    )
    code = status.HTTP_202_ACCEPTED if accepted else status.HTTP_200_OK
    return JSONResponse(status_code=code, content=payload.model_dump())


def _http_error(exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _response(result: RecoveryResult) -> JSONResponse:
    if result.outcome is RecoveryOutcome.NOT_FOUND:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": _NOT_FOUND}
        )
    if result.outcome is RecoveryOutcome.REFUSED:
        code = result.refusal.value if result.refusal else _CONCURRENT_UPDATE
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": code}
        )
    if result.run is None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": _CONCURRENT_UPDATE},
        )
    accepted = result.outcome is RecoveryOutcome.QUEUED
    payload = ManualReprocessResponse(
        outcome="queued" if accepted else "existing",
        run_id=str(result.run.id),
        status=result.run.status.value,
        stuck_kind=result.stuck_kind.value if result.stuck_kind else None,
        position=result.position,
        eta_seconds=result.eta_seconds,
        lock_version=result.lock_version,
        worker_notified=result.worker_notified,
        last_error_code=result.run.last_error_code,
    )
    code = status.HTTP_202_ACCEPTED if accepted else status.HTTP_200_OK
    return JSONResponse(status_code=code, content=payload.model_dump())


def _capability(result: RecoveryCapability) -> ManualRecoveryCapabilityResponse:
    run = result.run
    return ManualRecoveryCapabilityResponse(
        can_reprocess=result.can_reprocess,
        refusal_code=result.refusal.value if result.refusal else None,
        stuck_kind=result.stuck_kind.value if result.stuck_kind else None,
        run_id=str(run.id) if run is not None else None,
        status=run.status.value if run is not None else None,
        last_phase=run.last_phase if run is not None else None,
        last_error_code=run.last_error_code if run is not None else None,
        position=result.position,
        eta_seconds=result.eta_seconds,
        lock_version=result.lock_version,
    )


__all__ = ["router"]
