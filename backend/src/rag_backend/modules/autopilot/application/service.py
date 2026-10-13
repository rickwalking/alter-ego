"""Use cases for the autopilot bounded context.

The unit of work stays with the caller: ``transition`` flushes the
conditional update and the outbox row, and does not commit.
"""

from __future__ import annotations

from uuid import UUID

from rag_backend.modules.autopilot.api.views import AutopilotRunView
from rag_backend.modules.autopilot.domain.models import TransitionCommand
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository


class AutopilotService:
    """Public use-case entry for reading a run and transitioning it."""

    def __init__(self, runs: AutopilotRunRepository) -> None:
        self._runs = runs

    async def transition(self, command: TransitionCommand) -> bool:
        """Apply one allowed transition. False when the compare-and-set loses."""
        return await self._runs.transition(command)

    async def get_run(self, run_id: UUID) -> AutopilotRunView | None:
        """Return a boundary-safe view, or None when the run does not exist."""
        run = await self._runs.get(run_id)
        if run is None:
            return None
        return AutopilotRunView(
            run_id=str(run.run_id),
            state=run.state.value,
            state_reason=run.state_reason,
        )
