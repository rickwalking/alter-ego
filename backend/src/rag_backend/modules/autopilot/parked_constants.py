"""Constants for the parked-workflow guard.

A workflow is parked when its checkpoint is neither waiting for a review nor
failed, and no run is in flight on the carousel row. That happens when a run
dies after its gate was approved: the checkpoint sits before the next node
and nothing will ever run it.

The grace period before the runner acts is generous next to the worker interval, so a
run that is being started or reaped is never raced. A re-drive recovers checkpoints
whose gate was approved (or whose node was mid-step) and whose next node never finished.
Held or published carousels are finished and never parked.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_IN_PROGRESS,
)

PARKED_GRACE_SECONDS = 600

REASON_ENGINE_PARKED = "engine_parked_no_run_in_flight"
LOG_RUNNER_REDRIVE = "autopilot_runner_redrive"

REDRIVABLE_PHASE_STATUSES = frozenset({PHASE_STATUS_APPROVED, PHASE_STATUS_IN_PROGRESS})

NEVER_PARKED_PHASES = frozenset({
    PHASE_FINAL_REVIEW,
    PHASE_APPROVED_HOLD,
    PHASE_PUBLISHED,
})
