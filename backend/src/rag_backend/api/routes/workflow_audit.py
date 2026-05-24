"""Workflow audit log and collaboration lock API (WF-004, WF-005, UI-021)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import (
    assert_audit_aggregate_access,
    assert_content_access,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.workflow_audit import (
    AcquireLockRequest,
    ContentLockResponse,
    WorkflowAuditEntryResponse,
    WorkflowAuditListResponse,
)
from rag_backend.application.services.optimistic_lock_service import OptimisticLockService
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.optimistic_locking import ERR_LOCK_HELD_BY_OTHER
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["workflow_audit"])


def _event_service() -> WorkflowEventService:
    settings = get_settings()
    publisher = get_event_publisher(settings.redis_url or None)
    return WorkflowEventService(publisher)


def _lock_service() -> OptimisticLockService:
    return OptimisticLockService()


@router.get(
    "/workflow-audit/{aggregate_type}/{aggregate_id}",
    response_model=WorkflowAuditListResponse,
    summary="Get workflow audit log",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_workflow_audit(
    request: Request,
    aggregate_type: str,
    aggregate_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> WorkflowAuditListResponse:
    """Return event-sourced audit trail for an aggregate (WF-004)."""
    await assert_audit_aggregate_access(db, aggregate_type, aggregate_id, current_user)
    service = _event_service()
    entries = await service.list_for_aggregate(db, aggregate_type, aggregate_id)
    return WorkflowAuditListResponse(
        items=[WorkflowAuditEntryResponse.model_validate(entry) for entry in entries],
        total=len(entries),
    )


@router.post(
    "/content/{content_id}/lock",
    response_model=ContentLockResponse,
    summary="Acquire edit lock",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def acquire_content_lock(
    request: Request,
    content_id: str,
    body: AcquireLockRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> ContentLockResponse:
    """Acquire collaborative edit lock (UI-021)."""
    await assert_content_access(db, content_id, body.content_type, current_user)
    service = _lock_service()
    try:
        lock = await service.acquire_lock(
            db,
            content_id=content_id,
            content_type=body.content_type,
            user_id=current_user.id,
            user_name=current_user.full_name,
            ttl_seconds=body.ttl_seconds,
        )
    except ValueError as exc:
        if str(exc) == ERR_LOCK_HELD_BY_OTHER:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ERR_LOCK_HELD_BY_OTHER,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from exc
    await db.commit()
    return ContentLockResponse(
        content_id=lock.content_id,
        content_type=lock.content_type,
        user_id=lock.user_id,
        user_name=lock.user_name,
        expires_at=lock.expires_at,
    )


@router.delete(
    "/content/{content_id}/lock",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Release edit lock",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def release_content_lock(
    request: Request,
    content_id: str,
    content_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> None:
    """Release collaborative edit lock."""
    await assert_content_access(db, content_id, content_type, current_user)
    service = _lock_service()
    await service.release_lock(
        db,
        content_id=content_id,
        content_type=content_type,
        user_id=current_user.id,
    )
    await db.commit()


@router.get(
    "/content/{content_id}/lock",
    response_model=ContentLockResponse | None,
    summary="Get active edit lock",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_content_lock(
    request: Request,
    content_id: str,
    content_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> ContentLockResponse | None:
    """Return active lock if another user is editing."""
    await assert_content_access(db, content_id, content_type, current_user)
    service = _lock_service()
    lock = await service.get_active_lock(db, content_id, content_type)
    if lock is None:
        return None
    return ContentLockResponse(
        content_id=lock.content_id,
        content_type=lock.content_type,
        user_id=lock.user_id,
        user_name=lock.user_name,
        expires_at=lock.expires_at,
    )


__all__ = ["router"]
