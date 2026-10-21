"""Timezone-aware wall clock for domain models.

``datetime.utcnow()`` is deprecated (Python 3.12) and returns a naive value,
while every persisted timestamp column is ``DateTime(timezone=True)``.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)
