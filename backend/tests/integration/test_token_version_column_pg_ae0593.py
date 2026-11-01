"""The ``users.token_version`` one-shot on Postgres.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``. Skipped
unless ``DATABASE_URL`` points at Postgres (CI's backend test job does).
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import token_version_column as column
from rag_backend.scripts.token_version_column import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_USERS_SQL = text(
    "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) NOT NULL,"
    " hashed_password VARCHAR(255) NOT NULL, must_change_password BOOLEAN NOT NULL)"
)
_SEED_SQL = text(
    "INSERT INTO users (id, email, hashed_password, must_change_password)"
    " VALUES ('u1', 'kept@example.com', 'hash-1', false)"
)
_COLUMN_SQL = text(
    "SELECT data_type, is_nullable, column_default FROM information_schema.columns"
    " WHERE table_schema = current_schema() AND table_name = 'users'"
    " AND column_name = 'token_version'"
)
_ROWS_SQL = text("SELECT id, email, hashed_password, token_version FROM users")
_INSERT_WITHOUT_VERSION_SQL = text(
    "INSERT INTO users (id, email, hashed_password, must_change_password)"
    " VALUES ('u2', 'new@example.com', 'hash-2', false)"
    " RETURNING token_version"
)


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _users_without_version() -> AsyncIterator[AsyncEngine]:
    """A ``users`` table shaped like prod before the column."""
    async with isolated_schema([]) as engine:
        async with engine.begin() as conn:
            await conn.execute(_USERS_SQL)
            await conn.execute(_SEED_SQL)
        yield engine


async def _column(engine: AsyncEngine) -> tuple[str, str, str] | None:
    async with engine.connect() as conn:
        row = (await conn.execute(_COLUMN_SQL)).first()
    return None if row is None else (str(row[0]), str(row[1]), str(row[2]))


# Scenario: The token version column is added on prod by a one-shot
@requires_postgres
async def test_apply_adds_a_not_null_zero_column_and_keeps_rows() -> None:
    async with _users_without_version() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        added = await _column(engine)
        async with engine.begin() as conn:
            rows = [tuple(row) for row in await conn.execute(_ROWS_SQL)]
            inserted = (await conn.execute(_INSERT_WITHOUT_VERSION_SQL)).scalar_one()

    assert code == EXIT_OK
    assert added == ("integer", "NO", "0")
    assert rows == [("u1", "kept@example.com", "hash-1", 0)]
    assert inserted == 0


# Scenario: The token version column is added on prod by a one-shot
@requires_postgres
async def test_second_apply_changes_nothing() -> None:
    async with _users_without_version() as engine:
        first = await column.apply(engine)
        second = await column.apply(engine)
        verified = await column.verify(engine)

    assert first.added is True
    assert second.added is False
    assert column.format_report(second) == ["users token_version: present"]
    assert verified.missing is False


# Scenario: Verify fails while token_version is missing
@requires_postgres
async def test_verify_fails_while_the_column_is_missing() -> None:
    async with _users_without_version() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await column.verify(engine)
        still_missing = await _column(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.missing is True
    assert column.format_report(report) == [
        "users token_version: MISSING token_version"
    ]
    assert still_missing is None


# Scenario: The token version one-shot leaves other databases alone
@requires_postgres
async def test_a_database_without_users_is_left_alone() -> None:
    async with isolated_schema([]) as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        applied = await column.apply(engine)
        verified = await column.verify(engine)

    assert code == EXIT_OK
    assert applied == column.VersionColumnReport(supported=True)
    assert verified == column.VersionColumnReport(supported=True)


# Scenario: The token version column is added on prod by a one-shot
@requires_postgres
async def test_apply_only_adds_the_column_and_exits_0() -> None:
    async with _users_without_version() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=False))
        report = await column.verify(engine)

    assert code == EXIT_OK
    assert report.missing is False
