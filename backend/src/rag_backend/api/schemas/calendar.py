"""Pydantic schemas for content calendar API."""

from datetime import datetime

from pydantic import BaseModel, Field

from rag_backend.domain.constants.content_calendar import CalendarContentType


class CalendarItemResponse(BaseModel):
    """Single calendar entry."""

    id: str
    content_type: CalendarContentType
    title: str
    status: str
    event_date: str
    is_scheduled: bool = False
    phase: str | None = None
    phase_status: str | None = None


class ContentCalendarResponse(BaseModel):
    """Calendar view response."""

    items: list[CalendarItemResponse]
    start: datetime
    end: datetime
    total: int = Field(default=0)


class SchedulePublishRequest(BaseModel):
    """Schedule a blog post for future publication."""

    scheduled_publish_at: datetime


__all__ = ["CalendarItemResponse", "ContentCalendarResponse", "SchedulePublishRequest"]
