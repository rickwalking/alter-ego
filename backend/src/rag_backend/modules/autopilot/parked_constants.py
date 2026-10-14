"""Constants for the parked-workflow guard (AE-0363).

A workflow is parked when its checkpoint is neither waiting for a review nor
failed, and no run is in flight on the carousel row. That happens when a run
dies after its gate was approved: the checkpoint sits before the next node
and nothing will ever run it.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_IN_PROGRESS,
)

# How long a parked workflow may sit before the runner acts. Generous next to
# the worker interval so a run that is being started or reaped is never raced.
PARKED_GRACE_SECONDS = 600

REASON_ENGINE_PARKED = "engine_parked_no_run_in_flight"
LOG_RUNNER_REDRIVE = "autopilot_runner_redrive"

# Checkpoint statuses a re-drive can recover: the gate was approved (or the
# node was mid-step) and the next node never finished.
REDRIVABLE_PHASE_STATUSES = frozenset({PHASE_STATUS_APPROVED, PHASE_STATUS_IN_PROGRESS})

# Phases that are never parked: a held or published carousel is finished.
NEVER_PARKED_PHASES = frozenset({
    PHASE_FINAL_REVIEW,
    PHASE_APPROVED_HOLD,
    PHASE_PUBLISHED,
})
