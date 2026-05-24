"""Content calendar API (SCHED-002, UI-020)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireContentCalendar
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.calendar import CalendarItemResponse, ContentCalendarResponse
from rag_backend.application.services.content_calendar_service import ContentCalendarService
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.constants.workflow_validation import (
    ERR_CALENDAR_RANGE_INVALID,
    ERR_CALENDAR_RANGE_TOO_LARGE,
    MAX_CALENDAR_RANGE_DAYS,
)
from rag_backend.domain.models.user import UserRole

router = APIRouter(tags=["content_calendar"], dependencies=[RequireContentCalendar])


@router.get(
    "/content-calendar",
    response_model=ContentCalendarResponse,
    summary="Get content calendar view",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_content_calendar(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> ContentCalendarResponse:
    """Return scheduled and published content for calendar UI."""
    now = datetime.now(UTC)
    range_start = start or now - timedelta(days=30)
    range_end = end or now + timedelta(days=60)
    if range_start.tzinfo is None:
        range_start = range_start.replace(tzinfo=UTC)
    if range_end.tzinfo is None:
        range_end = range_end.replace(tzinfo=UTC)
    if range_end <= range_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_CALENDAR_RANGE_INVALID,
        )
    if (range_end - range_start).days > MAX_CALENDAR_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_CALENDAR_RANGE_TOO_LARGE,
        )
    author_filter = None if current_user.role == UserRole.ADMIN.value else current_user.id
    service = ContentCalendarService()
    items = await service.get_calendar(
        db,
        start=range_start,
        end=range_end,
        author_id=author_filter,
    )
    return ContentCalendarResponse(
        items=[CalendarItemResponse.model_validate(item) for item in items],
        start=range_start,
        end=range_end,
        total=len(items),
    )


__all__ = ["router"]
