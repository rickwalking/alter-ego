"""Timezone-aware wall clock for domain models.

``datetime.utcnow()`` is deprecated (Python 3.12) and returns a naive value,
while every persisted timestamp column is ``DateTime(timezone=True)`` (enforced by
``tests/unit/infrastructure/test_timestamp_columns_are_aware_ae0446.py``).
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)
