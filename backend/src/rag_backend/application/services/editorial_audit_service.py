"""Editorial audit logging for all content actions (SEC-001)."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class _AuditEntry:
    """Bundles common audit parameters to reduce method argument count (PLR0913)."""

    post_id: str
    user_id: str
    extra: object = None


@dataclass
class _EmitParams:
    """Bundles parameters for _emit to stay within max-args=3."""

    event_type: str
    entry: _AuditEntry
    payload: dict[str, object]


class EditorialAuditService:
    """Typed helpers for editorial audit events."""

    def __init__(self, event_service: WorkflowEventService) -> None:
        self._events = event_service

    async def log_created(self, db: AsyncSession, *, entry: _AuditEntry) -> str:
        return await self._emit(
            db,
            params=_EmitParams(
                event_type=EVENT_TYPE_BLOGPOST_CREATED,
                entry=entry,
                payload={"title": entry.extra},
            ),
        )

    async def log_updated(self, db: AsyncSession, *, entry: _AuditEntry) -> str:
        return await self._emit(
            db,
            params=_EmitParams(
                event_type=EVENT_TYPE_BLOGPOST_UPDATED,
                entry=entry,
                payload={"fields": entry.extra},
            ),
        )

    async def log_deleted(self, db: AsyncSession, *, entry: _AuditEntry) -> str:
        return await self._emit(
            db,
            params=_EmitParams(
                event_type=EVENT_TYPE_BLOGPOST_DELETED,
                entry=entry,
                payload={},
            ),
        )

    async def log_comment_added(self, db: AsyncSession, *, entry: _AuditEntry) -> str:
        return await self._emit(
            db,
            params=_EmitParams(
                event_type=EVENT_TYPE_BLOGPOST_COMMENT_ADDED,
                entry=entry,
                payload={"comment_id": entry.extra},
            ),
        )

    async def log_version_restored(
        self, db: AsyncSession, *, entry: _AuditEntry
    ) -> str:
        return await self._emit(
            db,
            params=_EmitParams(
                event_type=EVENT_TYPE_BLOGPOST_VERSION_RESTORED,
                entry=entry,
                payload={"version_number": entry.extra},
            ),
        )

    async def log_ai_action(self, db: AsyncSession, *, entry: _AuditEntry) -> str:
        return await self._emit(
            db,
            params=_EmitParams(
                event_type=EVENT_TYPE_BLOGPOST_AI_ACTION,
                entry=entry,
                payload={"action": entry.extra},
            ),
        )

    async def _emit(
        self,
        db: AsyncSession,
        *,
        params: _EmitParams,
    ) -> str:
        return await self._events.emit(
            db,
            event_type=params.event_type,
            aggregate_id=params.entry.post_id,
            aggregate_type=AGGREGATE_TYPE_BLOG_POST,
            payload=params.payload,
            metadata={
                "user_id": params.entry.user_id,
                "source": EVENT_SOURCE_EDITORIAL,
            },
        )


__all__ = ["EditorialAuditService", "_AuditEntry"]
