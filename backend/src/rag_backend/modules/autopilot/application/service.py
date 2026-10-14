"""Use cases for the autopilot bounded context.

The unit of work stays with the caller: ``transition`` flushes the
conditional update and the outbox row, and does not commit.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.api.views import (
    AutopilotRunView,
    InstagramStatusView,
)
from rag_backend.modules.autopilot.constants import STATE_UNPUBLISHED
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository
from rag_backend.modules.autopilot.domain.publish_claims import ManualRecord
from rag_backend.modules.autopilot.recovery_constants import MANUAL_STATE_FAILED


class ManualPublishLedger(Protocol):
    """Reads the manual publish of a carousel that has no autopilot run."""

    async def manual_record(self, project_id: str) -> ManualRecord | None:
        """The stored manual publish, if any."""
        ...


class AutopilotService:
    """Public use-case entry for reading a run and transitioning it."""

    def __init__(
        self,
        runs: AutopilotRunRepository,
        manual: ManualPublishLedger | None = None,
    ) -> None:
        self._runs = runs
        self._manual = manual

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

    async def instagram_status(self, project_id: str) -> InstagramStatusView:
        """Return the persisted Instagram publish state for a carousel."""
        run = await self._runs.find_by_carousel(project_id)
        if run is not None or self._manual is None:
            return _status_view(run)
        record = await self._manual.manual_record(project_id)
        if record is None:
            return _status_view(None)
        return _manual_view(record)


def _status_view(run: AutopilotRun | None) -> InstagramStatusView:
    if run is None:
        return InstagramStatusView(
            state=STATE_UNPUBLISHED,
            ig_post_id=None,
            permalink=None,
            error=None,
        )
    error = None
    if run.state is AutopilotRunState.PUBLISH_FAILED:
        error = run.state_reason
    return InstagramStatusView(
        state=run.state.value,
        ig_post_id=run.ig_post_id,
        permalink=run.ig_permalink,
        error=error,
    )


def _manual_view(record: ManualRecord) -> InstagramStatusView:
    error = record.error if record.state == MANUAL_STATE_FAILED else None
    return InstagramStatusView(
        state=record.state,
        ig_post_id=record.ig_post_id,
        permalink=record.ig_permalink,
        error=error,
    )
