"""Put a parked autopilot run back into the generation queue (owner retry, daily scan).

An ``escalated`` run moves to ``generating`` and resumes from its checkpoint; its
dead-lettered generation run, if any, is requeued in the same transaction. A
``failed`` run is terminal, so a run the queue failed before it started gets a new
queued run for the same theme. Discard closes a parked run instead. The caller
decides which runs are eligible.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.domain.dead_letter import (
    DeadLetterRuns,
    RetryFailedCommand,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository, Clock
from rag_backend.modules.autopilot.domain.queue_position import QueueControl
from rag_backend.modules.autopilot.queue_constants import REASON_DEAD_DISCARD


@dataclass(frozen=True, kw_only=True)
class ReviveDependencies:
    """Ports bound to one transaction; the caller commits."""

    runs: AutopilotRunRepository
    clock: Clock
    queue: QueueControl | None = None
    dead_letters: DeadLetterRuns | None = None


async def revive(
    deps: ReviveDependencies, run: AutopilotRun, reason: str
) -> UUID | None:
    """The run now queued for ``run``, or None when nothing moved."""
    if run.state is AutopilotRunState.ESCALATED:
        moved = await deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.ESCALATED,
                new=AutopilotRunState.GENERATING,
                reason=reason,
            )
        )
        if moved and deps.queue is not None:
            await deps.queue.requeue_dead_letter(run.run_id)
        return run.run_id if moved else None
    if run.state is not AutopilotRunState.FAILED or deps.dead_letters is None:
        return None
    new_run_id = uuid4()
    retried = await deps.dead_letters.retry_failed(
        RetryFailedCommand(
            run_id=run.run_id,
            new_run_id=new_run_id,
            created_at=deps.clock.now(),
            reason=reason,
        )
    )
    return new_run_id if retried else None


async def discard_parked(deps: ReviveDependencies, run: AutopilotRun) -> bool:
    """Close a run the queue parked: escalated → rejected, a failed run marked."""
    if run.state is AutopilotRunState.ESCALATED:
        return await deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.ESCALATED,
                new=AutopilotRunState.REJECTED,
                reason=REASON_DEAD_DISCARD,
            )
        )
    if run.state is not AutopilotRunState.FAILED or deps.dead_letters is None:
        return False
    return await deps.dead_letters.discard_failed(run.run_id)


__all__ = ["ReviveDependencies", "discard_parked", "revive"]
