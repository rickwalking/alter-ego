"""POV calendar rules (AE-0377, ADR-0021 D10). Pure, no I/O.

- ``sao_paulo_week``: the Monday-to-Monday São Paulo week, for the Radar IA
  weekly cap (growth plan 16.4 #10).
- ``POV_SLOT_WEEKDAYS`` / ``POV_SLOT_TIME``: the plan's Tuesday and Thursday
  12:00 São Paulo slot. Since AE-0404 it is the POV prior of the slot
  recommender (``domain/recommend.py``), which picks the auto ``next_slot``.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from rag_backend.domain.constants.content_mode import CONTENT_MODE_POV
from rag_backend.modules.autopilot.constants import DAILY_CAP_TIMEZONE
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.pov_constants import DAYS_PER_WEEK

# Growth plan section 8: Tuesday and Thursday, about 12:00 BRT.
POV_SLOT_WEEKDAYS: frozenset[int] = frozenset({1, 3})
POV_SLOT_TIME = time(hour=12, minute=0)


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


def run_content_mode(run: AutopilotRun) -> str | None:
    """A run with a confirmed thesis is POV; the rest are Radar IA (None)."""
    if run.pov_thesis:
        return CONTENT_MODE_POV
    return None


def is_pov_run(run: AutopilotRun) -> bool:
    """PR #106 review: a POV run always lands on its Tue/Thu 12:00 slot."""
    return run_content_mode(run) == CONTENT_MODE_POV


__all__ = [
    "POV_SLOT_TIME",
    "POV_SLOT_WEEKDAYS",
    "is_pov_run",
    "run_content_mode",
    "sao_paulo_week",
]
