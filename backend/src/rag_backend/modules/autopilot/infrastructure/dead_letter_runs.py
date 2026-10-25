"""``DeadLetterRuns`` on the webhook's session.

A run the queue failed before it started stays ``failed`` (terminal); the retry
marks its reason ``owner_queue_retry`` (or ``owner_queue_discard``) in one
compare-and-set and queues a new run
for the same theme, so a second tap finds nothing to retry. Nothing here commits.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.dead_letter import RetryFailedCommand
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.ports import QueuedRunCommand
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.queue_constants import (
    REASON_DEAD_DISCARD,
    REASON_DEAD_LETTER_PREFIX,
    REASON_DEAD_RETRY,
)

_R = AutopilotRunModel


class SqlDeadLetterRuns:
    """Implements ``DeadLetterRuns``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retry_failed(self, command: RetryFailedCommand) -> bool:
        """Mark the failed run retried and queue the new run; False when already."""
        if not await self._resolve(command.run_id, REASON_DEAD_RETRY):
            return False
        topic = await self._session.scalar(
            select(_R.topic_candidate_id).where(_R.id == command.run_id)
        )
        if topic is None:
            return False
        await SqlAlchemyTopicIntakeStore(self._session).add_queued_run(
            QueuedRunCommand(
                run_id=command.new_run_id,
                topic_candidate_id=topic,
                created_at=command.created_at,
            )
        )
        return True

    async def discard_failed(self, run_id: UUID) -> bool:
        """Mark the failed run discarded; False when it was already resolved."""
        return await self._resolve(run_id, REASON_DEAD_DISCARD)

    async def _resolve(self, run_id: UUID, reason: str) -> bool:
        result = await self._session.execute(
            update(_R)
            .where(
                _R.id == run_id,
                _R.state == AutopilotRunState.FAILED.value,
                _R.state_reason.startswith(REASON_DEAD_LETTER_PREFIX),
            )
            .values(state_reason=reason)
        )
        return cast(CursorResult[object], result).rowcount == 1


__all__ = ["SqlDeadLetterRuns"]
