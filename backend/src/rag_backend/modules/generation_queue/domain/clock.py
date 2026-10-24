"""The wall clock the queue uses when no test clock is injected."""

from __future__ import annotations

from datetime import datetime

from rag_backend.domain.clock import utc_now


class UtcClock:
    """Implements ``Clock`` with the real aware UTC time."""

    @staticmethod
    def now() -> datetime:
        """The current aware UTC time."""
        return utc_now()


UTC_CLOCK = UtcClock()

__all__ = ["UTC_CLOCK", "UtcClock"]
