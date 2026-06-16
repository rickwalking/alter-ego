"""Content calendar API (SCHED-002, UI-020).

Thin HTTP adapter (AE-0131). The blog+carousel item merge reads through the
publishing facade's read projection (the sole carousel/blog ORM read seam behind
the :class:`PublishingReadPort`). The route keeps the range validation + the
admin/author scope at the edge and maps the projection items one-to-one onto the
existing ``CalendarItemResponse`` schema (byte-identical).
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireContentCalendar
from rag_backend.api.dependencies.publishing import (
    PublishingComposition,
    build_publishing_module,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.deps import get_carousel_repo
from rag_backend.api.schemas.calendar import (
    CalendarItemResponse,
    ContentCalendarResponse,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.constants.workflow_validation import (
    ERR_CALENDAR_RANGE_INVALID,
    ERR_CALENDAR_RANGE_TOO_LARGE,
    MAX_CALENDAR_RANGE_DAYS,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.modules.publishing import (
    CalendarItem,
    CalendarQuery,
    CarouselRepository,
    PublishingModule,
)

router = APIRouter(tags=["content_calendar"], dependencies=[RequireContentCalendar])


def _get_publishing_module(
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the content-calendar edge."""
    return build_publishing_module(
        PublishingComposition(session=db, carousel_repository=repo, with_read=True),
    )


def _to_item_response(item: CalendarItem) -> CalendarItemResponse:
    """Map a calendar projection item one-to-one onto the legacy response schema."""
    return CalendarItemResponse.model_validate({
        "id": item.id,
        "content_type": item.content_type,
        "title": item.title,
        "status": item.status,
        "event_date": item.event_date,
        "is_scheduled": item.is_scheduled,
        "phase": item.phase,
        "phase_status": item.phase_status,
    })


@router.get(
    "/content-calendar",
    response_model=ContentCalendarResponse,
    summary="Get content calendar view",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_content_calendar(
    request: Request,
    current_user: EditorUser,
    publishing: Annotated[PublishingModule, Depends(_get_publishing_module)],
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
    author_filter = (
        None if current_user.role == UserRole.ADMIN.value else current_user.id
    )
    projection = await publishing.service.project_calendar(
        CalendarQuery(
            start=range_start,
            end=range_end,
            author_id=author_filter,
        ),
    )
    return ContentCalendarResponse(
        items=[_to_item_response(item) for item in projection.items],
        start=range_start,
        end=range_end,
        total=len(projection.items),
    )


__all__ = ["router"]
