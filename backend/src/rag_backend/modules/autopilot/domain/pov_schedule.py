"""POV calendar rules (AE-0377, ADR-0021 D10). Pure, no I/O.

- ``sao_paulo_week``: the Monday-to-Monday São Paulo week, for the Radar IA
  weekly cap (growth plan 16.4 #10).
- ``PovPublishSlots`` / ``publish_slots_for``: the glue roadmap R6 needs. The
  scheduler itself is AE-0370 (``scheduled_at``, ``AUTOPILOT_DEFAULT_PUBLISH``
  = ``next_slot``); its publish choice asks ``publish_slots_for`` for the slots,
  so a POV run gets the next Tuesday or Thursday at 12:00 São Paulo first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from rag_backend.domain.constants.content_mode import CONTENT_MODE_POV
from rag_backend.modules.autopilot.constants import DAILY_CAP_TIMEZONE
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.schedule import next_slots
from rag_backend.modules.autopilot.pov_constants import DAYS_PER_WEEK
from rag_backend.modules.autopilot.schedule_constants import SCHEDULE_SLOT_COUNT

# Growth plan section 8: Tuesday and Thursday, about 12:00 BRT.
POV_SLOT_WEEKDAYS: frozenset[int] = frozenset({1, 3})
POV_SLOT_TIME = time(hour=12, minute=0)
# Same lead as AE-0370's slot list: a slot must be at least 15 minutes away.
POV_SLOT_MIN_LEAD = timedelta(minutes=15)
_SEARCH_DAYS = 14


def _zone() -> ZoneInfo:
    return ZoneInfo(DAILY_CAP_TIMEZONE)


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def sao_paulo_week(moment: datetime) -> tuple[datetime, datetime]:
    """UTC bounds of the São Paulo Monday 00:00 week containing ``moment``."""
    local = _utc(moment).astimezone(_zone())
    monday = local.date() - timedelta(days=local.weekday())
    start = datetime.combine(monday, time(0, 0), tzinfo=_zone())
    end = datetime.combine(monday + timedelta(days=DAYS_PER_WEEK), time(0, 0), _zone())
    return start.astimezone(UTC), end.astimezone(UTC)


@dataclass(frozen=True)
class PovPublishSlots:
    """Next Tuesday or Thursday at 12:00 São Paulo, at least 15 minutes ahead."""

    weekdays: frozenset[int] = POV_SLOT_WEEKDAYS
    at: time = POV_SLOT_TIME

    def next_slot(self, now: datetime) -> datetime:
        """The first matching slot at or after ``now`` + the minimum lead."""
        earliest = _utc(now) + POV_SLOT_MIN_LEAD
        start = earliest.astimezone(_zone()).date()
        for offset in range(_SEARCH_DAYS):
            slot = self._slot_on(start + timedelta(days=offset))
            if slot is not None and slot >= earliest:
                return slot
        msg = "no POV slot within two weeks"
        raise LookupError(msg)

    def _slot_on(self, day: date) -> datetime | None:
        if day.weekday() not in self.weekdays:
            return None
        return datetime.combine(day, self.at, tzinfo=_zone()).astimezone(UTC)


def slot_policy_for(content_mode: str | None) -> PovPublishSlots | None:
    """POV runs use Tue/Thu 12:00; None keeps AE-0370's default slots."""
    if content_mode == CONTENT_MODE_POV:
        return PovPublishSlots()
    return None


def run_content_mode(run: AutopilotRun) -> str | None:
    """A run with a confirmed thesis is POV; the rest are Radar IA (None)."""
    if run.pov_thesis:
        return CONTENT_MODE_POV
    return None


def publish_slots_for(run: AutopilotRun, now: datetime) -> tuple[datetime, ...]:
    """AE-0370's next slots; a POV run gets its Tue/Thu 12:00 slot first."""
    default = next_slots(now)
    policy = slot_policy_for(run_content_mode(run))
    if policy is None:
        return default
    first = policy.next_slot(now)
    rest = tuple(slot for slot in default if slot != first)
    return (first, *rest)[:SCHEDULE_SLOT_COUNT]


__all__ = [
    "POV_SLOT_MIN_LEAD",
    "POV_SLOT_TIME",
    "POV_SLOT_WEEKDAYS",
    "PovPublishSlots",
    "publish_slots_for",
    "run_content_mode",
    "sao_paulo_week",
    "slot_policy_for",
]
