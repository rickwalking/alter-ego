"""Compare-and-set steps for publish-now and scheduling.

Kept beside ``owner_steps.py``. Entering ``scheduled`` needs the time, so
``schedule_command`` / ``reschedule_command`` build that step per tap.

``SCHEDULED_PUBLISH_NOW_STEP``: "Publicar agora" on a scheduled run publishes
immediately. ``UNSCHEDULE_STEP``: "Cancelar agendamento" goes back to the
review. ``SCHEDULE_REFUSED_STEP``: the editorial approve refused the schedule,
so the review stays open.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from rag_backend.modules.autopilot.application.owner_steps import OwnerStep
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.recovery_constants import REASON_APPROVE_REFUSED
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_OWNER_PUBLISH_NOW,
    REASON_OWNER_RESCHEDULED,
    REASON_OWNER_SCHEDULED,
    REASON_OWNER_UNSCHEDULED,
)

_AWAITING = AutopilotRunState.AWAITING_OWNER
_SCHEDULED = AutopilotRunState.SCHEDULED
_PUBLISHING = AutopilotRunState.PUBLISHING

SCHEDULED_PUBLISH_NOW_STEP = OwnerStep(
    expected=_SCHEDULED,
    new=_PUBLISHING,
    reason=REASON_OWNER_PUBLISH_NOW,
)
UNSCHEDULE_STEP = OwnerStep(
    expected=_SCHEDULED,
    new=_AWAITING,
    reason=REASON_OWNER_UNSCHEDULED,
)
SCHEDULE_REFUSED_STEP = OwnerStep(
    expected=_SCHEDULED,
    new=_AWAITING,
    reason=REASON_APPROVE_REFUSED,
)


def schedule_command(run_id: UUID, at: datetime) -> TransitionCommand:
    """``awaiting_owner -> scheduled`` at ``at``."""
    return TransitionCommand(
        run_id=run_id,
        expected=_AWAITING,
        new=_SCHEDULED,
        reason=REASON_OWNER_SCHEDULED,
        scheduled_at=at,
    )


def reschedule_command(run_id: UUID, at: datetime) -> TransitionCommand:
    """``scheduled -> scheduled`` with the new time; the due tick races safely."""
    return TransitionCommand(
        run_id=run_id,
        expected=_SCHEDULED,
        new=_SCHEDULED,
        reason=REASON_OWNER_RESCHEDULED,
        scheduled_at=at,
    )
