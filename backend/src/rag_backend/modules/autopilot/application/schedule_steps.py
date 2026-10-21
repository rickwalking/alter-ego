"""Compare-and-set steps for publish-now and scheduling.

Kept beside ``owner_steps.py``. Entering ``scheduled`` needs the time, so
that step is built per tap in ``publish_choice``.

``SCHEDULED_PUBLISH_NOW_STEP``: "Publicar agora" on a scheduled run publishes
immediately. ``UNSCHEDULE_STEP``: "Cancelar agendamento" goes back to the
review. ``SCHEDULE_REFUSED_STEP``: the editorial approve refused the schedule,
so the review stays open.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.application.owner_steps import OwnerStep
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.recovery_constants import REASON_APPROVE_REFUSED
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_OWNER_PUBLISH_NOW,
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
