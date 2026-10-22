"""Timestamp column factories shared by the ORM models.

Scenario: created_at is timezone-aware, server-defaulted and not null.
Scenario: updated_at also refreshes on update.
Scenario: every call returns a fresh column.
"""

from __future__ import annotations

from sqlalchemy import DateTime

from rag_backend.infrastructure.database.models.columns import (
    created_at_column,
    updated_at_column,
)


# Scenario: created_at is timezone-aware, server-defaulted and not null.
def test_created_at_is_timezone_aware_server_default_not_null() -> None:
    column = created_at_column()

    assert isinstance(column.type, DateTime)
    assert column.type.timezone is True
    assert column.server_default is not None
    assert column.nullable is False
    assert column.onupdate is None


# Scenario: updated_at also refreshes on update.
def test_updated_at_refreshes_on_update() -> None:
    column = updated_at_column()

    assert column.type.timezone is True
    assert column.server_default is not None
    assert column.onupdate is not None
    assert column.nullable is False


# Scenario: every call returns a fresh column.
def test_each_call_returns_a_fresh_column() -> None:
    assert created_at_column() is not created_at_column()
    assert updated_at_column() is not updated_at_column()
