"""SQLAlchemy adapter for ``RunRecoveryStore`` (AE-0348 QA round 1)."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.recovery import (
    EscalatedScan,
    EscalationMark,
    ReworkIntent,
    UnnotifiedMark,
    WakeCheck,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.run_mapping import run_from_row
from rag_backend.modules.autopilot.notify_constants import (
    REASON_NOTIFIER_UNCONFIGURED,
)


class SqlRunRecoveryStore:
    """Session-scoped. Writes never touch ``state``.

    Only ``mark_unnotified`` moves ``updated_at``: it restarts the close clock.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def queue_rework(self, intent: ReworkIntent) -> bool:
        """Store phase and feedback while the run is ``reworking``."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == intent.run_id,
                AutopilotRunModel.state == AutopilotRunState.REWORKING.value,
            )
            .values(rework_phase=intent.phase, rework_feedback=intent.feedback)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def clear_rework(self, run_id: UUID) -> None:
        """Forget the queued rework."""
        await self._session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == run_id)
            .values(rework_phase=None, rework_feedback=None)
        )

    async def mark_escalated(self, mark: EscalationMark) -> None:
        """Remember the lock version the run was escalated at."""
        await self._session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == mark.run_id)
            .values(escalated_version=mark.version)
        )

    async def escalated_for_check(self, scan: EscalatedScan) -> list[AutopilotRun]:
        """Never-checked runs first, then the least recently checked (QA r2 R1)."""
        checked = AutopilotRunModel.wake_checked_at
        result = await self._session.execute(
            select(AutopilotRunModel)
            .where(AutopilotRunModel.state == AutopilotRunState.ESCALATED.value)
            .order_by(
                checked.is_not(None),
                checked.asc(),
                AutopilotRunModel.updated_at.asc(),
            )
            .limit(scan.limit)
            .execution_options(populate_existing=True)
        )
        return [run_from_row(row) for row in result.scalars().all()]

    async def mark_checked(self, check: WakeCheck) -> None:
        """Stamp ``wake_checked_at`` so the next sweep starts with other runs."""
        await self._session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == check.run_id)
            .values(wake_checked_at=check.at)
        )

    async def mark_unnotified(self, mark: UnnotifiedMark) -> bool:
        """Record ``notifier_unconfigured`` on a still-escalated run."""
        result = await self._session.execute(
            update(AutopilotRunModel)
            .where(
                AutopilotRunModel.id == mark.run_id,
                AutopilotRunModel.state == AutopilotRunState.ESCALATED.value,
            )
            .values(state_reason=REASON_NOTIFIER_UNCONFIGURED, updated_at=mark.at)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def rollback(self) -> None:
        """Discard the session's pending work."""
        await self._session.rollback()
