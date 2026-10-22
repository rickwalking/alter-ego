"""Column factories shared by the ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func


def created_at_column() -> Column[datetime]:
    """Timezone-aware, database-defaulted creation timestamp."""
    return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def updated_at_column() -> Column[datetime]:
    """Timezone-aware, database-defaulted timestamp refreshed on every update."""
    return Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
