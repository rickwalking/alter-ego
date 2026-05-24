"""Editorial audit logging for all content actions (SEC-001)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    EVENT_SOURCE_EDITORIAL,
    EVENT_TYPE_BLOGPOST_AI_ACTION,
    EVENT_TYPE_BLOGPOST_COMMENT_ADDED,
    EVENT_TYPE_BLOGPOST_CREATED,
    EVENT_TYPE_BLOGPOST_DELETED,
    EVENT_TYPE_BLOGPOST_UPDATED,
    EVENT_TYPE_BLOGPOST_VERSION_RESTORED,
)


class EditorialAuditService:
    """Typed helpers for editorial audit events."""

    def __init__(self, event_service: WorkflowEventService) -> None:
        self._events = event_service

    async def log_created(self, db: AsyncSession, post_id: str, user_id: str, title: str) -> str:
        return await self._emit(db, EVENT_TYPE_BLOGPOST_CREATED, post_id, {"title": title}, user_id)

    async def log_updated(
        self, db: AsyncSession, post_id: str, user_id: str, fields: list[str]
    ) -> str:
        return await self._emit(
            db, EVENT_TYPE_BLOGPOST_UPDATED, post_id, {"fields": fields}, user_id
        )

    async def log_deleted(self, db: AsyncSession, post_id: str, user_id: str) -> str:
        return await self._emit(db, EVENT_TYPE_BLOGPOST_DELETED, post_id, {}, user_id)

    async def log_comment_added(
        self, db: AsyncSession, post_id: str, user_id: str, comment_id: str
    ) -> str:
        return await self._emit(
            db,
            EVENT_TYPE_BLOGPOST_COMMENT_ADDED,
            post_id,
            {"comment_id": comment_id},
            user_id,
        )

    async def log_version_restored(
        self, db: AsyncSession, post_id: str, user_id: str, version_number: int
    ) -> str:
        return await self._emit(
            db,
            EVENT_TYPE_BLOGPOST_VERSION_RESTORED,
            post_id,
            {"version_number": version_number},
            user_id,
        )

    async def log_ai_action(self, db: AsyncSession, post_id: str, user_id: str, action: str) -> str:
        return await self._emit(
            db, EVENT_TYPE_BLOGPOST_AI_ACTION, post_id, {"action": action}, user_id
        )

    async def _emit(
        self,
        db: AsyncSession,
        event_type: str,
        post_id: str,
        payload: dict[str, object],
        user_id: str,
    ) -> str:
        return await self._events.emit(
            db,
            event_type=event_type,
            aggregate_id=post_id,
            aggregate_type=AGGREGATE_TYPE_BLOG_POST,
            payload=payload,
            metadata={"user_id": user_id, "source": EVENT_SOURCE_EDITORIAL},
        )


__all__ = ["EditorialAuditService"]
