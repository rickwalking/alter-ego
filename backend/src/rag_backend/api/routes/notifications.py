"""API routes for in-app notifications (NOTIF-001, UI-019, UI-022)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import (
    assert_content_owner_or_admin,
    assign_content_reviewer,
    validate_reviewer_user,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.notifications import (
    NotificationListResponse,
    NotificationResponse,
    ReviewAssignmentRequest,
)
from rag_backend.application.services.notification_service import NotificationService
from rag_backend.domain.constants.notifications import ERR_NOTIFICATION_NOT_FOUND
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS

router = APIRouter(tags=["notifications"])


def _notification_service() -> NotificationService:
    return NotificationService()


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="List notifications for current user",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def list_notifications(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    """Return in-app notifications (UI-019)."""
    service = _notification_service()
    items = await service.list_for_user(db, current_user.id, unread_only=unread_only)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def mark_notification_read(
    request: Request,
    notification_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> NotificationResponse:
    """Mark a notification read."""
    service = _notification_service()
    notification = await service.mark_read(db, notification_id, current_user.id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_NOTIFICATION_NOT_FOUND,
        )
    await db.commit()
    return NotificationResponse.model_validate(notification)


@router.post(
    "/notifications/assign-review",
    response_model=NotificationResponse,
    summary="Assign reviewer and send notification",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def assign_reviewer(
    request: Request,
    body: ReviewAssignmentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> NotificationResponse:
    """Assign a reviewer and notify them (UI-022)."""
    await assert_content_owner_or_admin(
        db, body.content_id, body.content_type, current_user
    )
    await validate_reviewer_user(db, body.reviewer_id)
    await assign_content_reviewer(
        db, body.content_id, body.content_type, body.reviewer_id
    )
    service = _notification_service()
    notification = await service.create_review_request(
        db,
        user_id=body.reviewer_id,
        content_id=body.content_id,
        content_type=body.content_type,
        title=body.title,
        deadline_hours=body.deadline_hours,
    )
    await db.commit()
    return NotificationResponse.model_validate(notification)


__all__ = ["router"]
