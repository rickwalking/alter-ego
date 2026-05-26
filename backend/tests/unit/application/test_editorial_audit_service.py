"""Unit tests for editorial audit service (SEC-001)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.editorial_audit_service import (
    EditorialAuditService,
)
from rag_backend.domain.constants.workflow_events import EVENT_TYPE_BLOGPOST_UPDATED


@pytest.mark.asyncio
async def test_log_updated_emits_event() -> None:
    # Scenario: Editorial audit logs content updates
    event_service = MagicMock()
    event_service.emit = AsyncMock(return_value="evt-1")
    audit = EditorialAuditService(event_service)
    db = AsyncMock()

    event_id = await audit.log_updated(db, "post-1", "user-1", ["title"])

    assert event_id == "evt-1"
    event_service.emit.assert_awaited_once()
    call_kwargs = event_service.emit.call_args.kwargs
    assert call_kwargs["event_type"] == EVENT_TYPE_BLOGPOST_UPDATED
    assert call_kwargs["aggregate_id"] == "post-1"
