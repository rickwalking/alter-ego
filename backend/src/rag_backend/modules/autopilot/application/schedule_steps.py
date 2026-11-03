"""Compare-and-set steps for publish-now and scheduling.

Kept beside ``owner_steps.py``. Entering ``scheduled`` needs the time, so
``schedule_command`` / ``reschedule_command`` build that step per tap.

``SCHEDULED_PUBLISH_NOW_STEP``: "Publicar agora" on a scheduled run publishes
immediately. ``UNSCHEDULE_STEP``: "Cancelar agendamento" goes back to the
review. ``SCHEDULE_REFUSED_STEP``: the editorial approve refused the schedule,
so the review stays open.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.modules.autopilot.application.owner_steps import OwnerStep
from rag_backend.modules.autopilot.domain.gate import ResumeStatus
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import PendingRework
from rag_backend.modules.autopilot.recovery_constants import REASON_APPROVE_REFUSED
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_OWNER_PUBLISH_NOW,
    REASON_OWNER_RESCHEDULED,
    REASON_OWNER_SCHEDULED,
    REASON_OWNER_UNSCHEDULED,
    SCHEDULE_PENDING_PHASE,
)
from rag_backend.modules.autopilot.webhook_constants import (
    TEXT_APPROVE_REFUSED,
    TEXT_APPROVE_RENDER_PENDING,
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


@dataclass(frozen=True, kw_only=True)
class ApproveRefusal:
    """A refused approve: the step that reopens the review, and why."""

    step: OwnerStep
    status: ResumeStatus

    @property
    def text(self) -> str:
        """The owner's message: the slides still render, or a generic refusal."""
        return refusal_text(self.status)


def refusal_text(status: ResumeStatus) -> str:
    """The owner's message for a refused approve."""
    if status is ResumeStatus.RENDER_PENDING:
        return TEXT_APPROVE_RENDER_PENDING
    return TEXT_APPROVE_REFUSED


def is_schedule_reply(pending: PendingRework) -> bool:
    """True when the owner's next text is a publish time, not rework feedback."""
    return pending.phase == SCHEDULE_PENDING_PHASE
