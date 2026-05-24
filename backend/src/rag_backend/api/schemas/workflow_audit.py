"""Pydantic schemas for workflow audit log API."""

from datetime import datetime

from pydantic import BaseModel, Field

from rag_backend.domain.constants.workflow_validation import (
    MAX_LOCK_TTL_SECONDS,
    MIN_LOCK_TTL_SECONDS,
)


class WorkflowAuditEntryResponse(BaseModel):
    """Single audit log entry."""

    id: str
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    version: int
    payload: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict, alias="metadata_json")
    stream_entry_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class WorkflowAuditListResponse(BaseModel):
    """Audit log list."""

    items: list[WorkflowAuditEntryResponse]
    total: int


class ContentLockResponse(BaseModel):
    """Active edit lock."""

    content_id: str
    content_type: str
    user_id: str
    user_name: str
    expires_at: datetime


class AcquireLockRequest(BaseModel):
    """Request to acquire an edit lock."""

    content_type: str
    ttl_seconds: int = Field(default=300, ge=MIN_LOCK_TTL_SECONDS, le=MAX_LOCK_TTL_SECONDS)


__all__ = [
    "AcquireLockRequest",
    "ContentLockResponse",
    "WorkflowAuditEntryResponse",
    "WorkflowAuditListResponse",
]
