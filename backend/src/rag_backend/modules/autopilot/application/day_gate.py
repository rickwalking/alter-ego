"""Once-per-day gate on the America/Sao_Paulo calendar."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from rag_backend.modules.autopilot.constants import DAILY_CAP_TIMEZONE
from rag_backend.modules.autopilot.domain.topic_text import as_utc


class SaoPauloDayGate:
    """Claims each local calendar day at most once for this process."""

    def __init__(self) -> None:
        self._claimed: date | None = None

    def claim(self, now: datetime) -> bool:
        """True the first time ``now`` falls on a new Sao Paulo day."""
        day = as_utc(now).astimezone(ZoneInfo(DAILY_CAP_TIMEZONE)).date()
        if self._claimed == day:
            return False
        self._claimed = day
        return True
