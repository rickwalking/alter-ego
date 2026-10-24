"""Reconcile the checkpoint status with the carousel row.

The policy used to read only the checkpoint. A checkpoint at
``content/approved`` with no run in flight made it wait forever. This pure
function returns the status the policy should see, and whether the workflow
is parked (and for how long), so the policy can re-drive or escalate.

A run that dies after the images gate, before the final review opens its
review, leaves the checkpoint reporting ``final_review/approved`` like a held
carousel. Only the engine tells them apart: the dead run has a pending node
and no open interrupt (``node_pending``), the held carousel does not.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.constants import (
    PHASE_STATUS_AWAITING,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.modules.autopilot.parked_constants import NEVER_PARKED_PHASES

_SETTLED = frozenset({PHASE_STATUS_AWAITING, PHASE_STATUS_FAILED})


@dataclass(frozen=True, kw_only=True)
class RowRun:
    """What the carousel row says about the run.

    ``idle_seconds`` is the time since the row last changed; ``None`` when
    the row has no timestamp.
    """

    phase_status: str
    idle_seconds: float | None


@dataclass(frozen=True, kw_only=True)
class GateStatusInput:
    """Checkpoint phase and status, the row facts, and the grace period.

    ``node_pending`` is the engine's word that a node waits to run with no
    review open (never the approved hold).
    """

    engine_phase: str
    engine_status: str
    row: RowRun | None
    grace_seconds: int
    node_pending: bool


@dataclass(frozen=True, kw_only=True)
class GateStatus:
    """The status the policy reads, and the parked facts."""

    phase_status: str
    parked: bool = False
    parked_overdue: bool = False


def reconcile_gate_status(given: GateStatusInput) -> GateStatus:
    """Pick the status the policy should act on.

    1. A run in flight on the row wins: the policy waits (or escalates when
       the heartbeat is stale).
    2. A checkpoint waiting for a review, or failed, is taken as is.
    3. A row a run marked ``failed`` is a failure the owner must see.
    4. A held or finished carousel is not parked, unless the engine still has
       a node pending (a run that died before the final review opened).
    5. Anything else is parked: nothing is running and nothing will.
    """
    row = given.row
    if row is not None and row.phase_status == PHASE_STATUS_IN_PROGRESS:
        return GateStatus(phase_status=PHASE_STATUS_IN_PROGRESS)
    if given.engine_status in _SETTLED:
        return GateStatus(phase_status=given.engine_status)
    if row is not None and row.phase_status == PHASE_STATUS_FAILED:
        return GateStatus(phase_status=PHASE_STATUS_FAILED)
    if given.engine_phase in NEVER_PARKED_PHASES and not given.node_pending:
        return GateStatus(phase_status=given.engine_status)
    return GateStatus(
        phase_status=given.engine_status,
        parked=True,
        parked_overdue=_overdue(row, given.grace_seconds),
    )


def _overdue(row: RowRun | None, grace_seconds: int) -> bool:
    """Unknown age counts as overdue, so a parked run is never silent."""
    if row is None or row.idle_seconds is None:
        return True
    return row.idle_seconds > grace_seconds
