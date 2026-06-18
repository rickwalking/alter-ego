"""Protocol for stuck-workflow auto-reject (AE-0210).

CLAUDE.md: "Auto-reject after timeout; never leave workflows stuck." The worker
depends on this domain contract; the concrete query/transition lives in
infrastructure so the application/worker layer gains no infrastructure import.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class StuckWorkflowAutoRejector(Protocol):
    """Transitions timed-out workflows to a terminal rejected state."""

    async def auto_reject_stuck(self, db: AsyncSession, timeout_hours: int) -> int:
        """Auto-reject every workflow idle past ``timeout_hours``.

        Returns the number of workflows transitioned to the terminal rejected
        state on this tick. Implementations emit the existing phase-changed
        event for each transition and must be idempotent across ticks.
        """
        ...


__all__ = ["StuckWorkflowAutoRejector"]
