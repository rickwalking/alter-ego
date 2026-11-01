"""The active-admin count asks the database to lock the rows it counts.

Scenarios: ``tests/features/last_active_admin_guard_ae0585.feature``. Runs with
no database: a session double captures the statement, which is compiled for
Postgres to check its ``FOR UPDATE`` clause.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pytest
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.user_repository import (
    PostgresUserRepository,
)

_LOCK_CLAUSE = "FOR UPDATE"
_IDS = ("a1", "a2")


class _Scalars:
    def all(self) -> list[str]:
        return list(_IDS)


class _Result:
    def scalars(self) -> _Scalars:
        return _Scalars()


@dataclass
class _CapturingSession:
    """Records every executed statement and returns two ids."""

    statements: list[Select[tuple[str]]] = field(default_factory=list)

    async def execute(self, statement: Select[tuple[str]]) -> _Result:
        self.statements.append(statement)
        return _Result()


@pytest.mark.unit
class TestActiveAdminCountLock:
    """``count_active_by_role`` selects the ids ``FOR UPDATE`` and counts them."""

    # Scenario: The active-admin count locks the rows it counts
    async def test_the_count_locks_the_rows_and_counts_them(self) -> None:
        session = _CapturingSession()
        repo = PostgresUserRepository(cast(AsyncSession, session))

        count = await repo.count_active_by_role(UserRole.ADMIN)

        assert count == len(_IDS)
        (statement,) = session.statements
        sql = str(statement.compile(dialect=PGDialect()))
        assert _LOCK_CLAUSE in sql
