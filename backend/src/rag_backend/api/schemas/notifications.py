"""Pydantic schemas for notifications API."""

from datetime import datetime

from pydantic import BaseModel, Field

from rag_backend.domain.constants.workflow_validation import (
    MAX_NOTIFICATION_TITLE_LENGTH,
    MAX_REVIEW_DEADLINE_HOURS,
    MIN_REVIEW_DEADLINE_HOURS,
)


class NotificationResponse(BaseModel):
    """Single notification."""

    id: str
    user_id: str
    notification_type: str
    title: str
    body: str | None = None
    status: str
    content_id: str | None = None
    content_type: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict, alias="metadata_json")
    deadline_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class NotificationListResponse(BaseModel):
    """Paginated notification list."""

    items: list[NotificationResponse]
    total: int


class ReviewAssignmentRequest(BaseModel):
    """Assign a reviewer to content."""

    reviewer_id: str
    content_id: str
    content_type: str
    title: str = Field(..., max_length=MAX_NOTIFICATION_TITLE_LENGTH)
    deadline_hours: int = Field(
        default=24, ge=MIN_REVIEW_DEADLINE_HOURS, le=MAX_REVIEW_DEADLINE_HOURS
    )


__all__ = [
    "NotificationListResponse",
    "NotificationResponse",
    "ReviewAssignmentRequest",
]
