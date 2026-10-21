"""Concurrent scout-failed POSTs respect the daily cap.

Gherkin: tests/features/autopilot_grok_bot_scout.feature
  Scenario: Concurrent scout failures respect the daily cap
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.modules.autopilot.application.scout_failure import (
    ScoutFailureCommand,
    ScoutFailureDependencies,
    ScoutFailureResult,
    ScoutFailureService,
)
from rag_backend.modules.autopilot.domain.notify import StatusNotice, StatusSendResult
from rag_backend.modules.autopilot.infrastructure.scout_failure_log import (
    OutboxScoutFailureLog,
)
from rag_backend.modules.autopilot.scout_constants import (
    DETAIL_SCOUT_DAILY_CAP,
    SCOUT_FAILURES_PER_DAY,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

pytestmark = [pytest.mark.integration, requires_postgres]

_NOW = datetime.now(UTC)
_SEND_DELAY_SECONDS = 0.05
_TABLES = (EventOutboxModel.__tablename__, WorkflowAuditLogModel.__tablename__)


class _SlowNotifier:
    """Yields while sending, so unserialized requests would all pass the cap."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        await asyncio.sleep(_SEND_DELAY_SECONDS)
        self.texts.append(notice.text)
        return StatusSendResult(message_id=len(self.texts))


class _Clock:
    def now(self) -> datetime:
        return _NOW


async def _report(
    engine: AsyncEngine, notifier: _SlowNotifier, reason: str
) -> ScoutFailureResult:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        service = ScoutFailureService(
            ScoutFailureDependencies(
                notifier=notifier,
                chat_id="4242",
                log=OutboxScoutFailureLog(session),
                clock=_Clock(),
            )
        )
        return await service.report(ScoutFailureCommand(reason=reason))


# Scenario: Concurrent scout failures respect the daily cap
@pytest.mark.asyncio
async def test_concurrent_failures_deliver_at_most_the_cap() -> None:
    notifier = _SlowNotifier()
    reasons = [f"failure {index}" for index in range(SCOUT_FAILURES_PER_DAY + 2)]
    async with isolated_schema(_TABLES) as engine:
        results = await asyncio.gather(
            *(_report(engine, notifier, reason) for reason in reasons)
        )

    delivered = [result for result in results if result.delivered]
    capped = [result for result in results if not result.delivered]
    assert len(delivered) == SCOUT_FAILURES_PER_DAY
    assert len(notifier.texts) == SCOUT_FAILURES_PER_DAY
    assert {result.error for result in capped} == {DETAIL_SCOUT_DAILY_CAP}
