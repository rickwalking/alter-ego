"""Add ``users.token_version`` on prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds a column to an existing table. So the column that revision
``c0d1e2f3a4b5`` adds for fresh databases reaches prod through this idempotent
one-shot instead, run by the deploy after the ``must_change_password`` step.

The column is ``INTEGER NOT NULL DEFAULT 0``: Postgres 11+ keeps a constant
default in the catalog, so existing rows read 0 without a table rewrite, and
the access tokens alive at deploy time (no ``tv`` claim, read as 0) keep
working. A short lock timeout makes a hand run with the stack up fail fast
instead of queueing every sign-in behind the ``ALTER``. A run that finds the
column already there issues no ``ALTER`` at all, so it takes no table lock;
``ADD COLUMN IF NOT EXISTS`` keeps a racing second run harmless. A database
without ``users`` yet is left alone (``create_all`` creates it with the
column), and a database that is not Postgres (SQLite in tests) is a no-op. The
SQL is fixed text, never built from input.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

USERS_TABLE = "users"
VERSION_COLUMN = "token_version"
POSTGRES_DIALECT = "postgresql"
REPORT_PREFIX = "users token_version"

_TABLE_PRESENT_SQL = text(
    "SELECT count(*) FROM information_schema.tables"
    " WHERE table_schema = current_schema() AND table_name = :table"
)
_COLUMN_PRESENT_SQL = text(
    "SELECT count(*) FROM information_schema.columns"
    " WHERE table_schema = current_schema()"
    " AND table_name = :table AND column_name = :column"
)
_LOCK_TIMEOUT_SQL = text("SET LOCAL lock_timeout = '5s'")
_ADD_VERSION_SQL = text(
    f"ALTER TABLE {USERS_TABLE} ADD COLUMN IF NOT EXISTS {VERSION_COLUMN}"
    " INTEGER NOT NULL DEFAULT 0"
)


@dataclass(frozen=True)
class VersionColumnReport:
    """What one run found and did."""

    supported: bool
    table_present: bool = False
    added: bool = False
    missing: bool = False


async def _state(conn: AsyncConnection) -> tuple[bool, bool]:
    """Whether ``users`` exists, and whether it already has the column."""
    table = bool(
        (await conn.execute(_TABLE_PRESENT_SQL, {"table": USERS_TABLE})).scalar()
    )
    if not table:
        return False, False
    params = {"table": USERS_TABLE, "column": VERSION_COLUMN}
    count = (await conn.execute(_COLUMN_PRESENT_SQL, params)).scalar()
    return True, bool(count)


def _unsupported(engine: AsyncEngine) -> bool:
    """True (and logged) when the database is not Postgres."""
    if engine.dialect.name == POSTGRES_DIALECT:
        return False
    logger.info("token_version_column_skipped", dialect=engine.dialect.name)
    return True


async def apply(engine: AsyncEngine) -> VersionColumnReport:
    """Add the column to an existing ``users`` table (one transaction)."""
    if _unsupported(engine):
        return VersionColumnReport(supported=False)
    async with engine.begin() as conn:
        table, column = await _state(conn)
        if not table:
            return VersionColumnReport(supported=True)
        if not column:
            await conn.execute(_LOCK_TIMEOUT_SQL)
            await conn.execute(_ADD_VERSION_SQL)
    logger.info("token_version_column_applied", added=not column)
    return VersionColumnReport(supported=True, table_present=True, added=not column)


async def verify(engine: AsyncEngine) -> VersionColumnReport:
    """Report whether an existing ``users`` table still lacks the column."""
    if _unsupported(engine):
        return VersionColumnReport(supported=False)
    async with engine.connect() as conn:
        table, column = await _state(conn)
    if not table:
        return VersionColumnReport(supported=True)
    logger.info("token_version_column_verified", missing=not column)
    return VersionColumnReport(supported=True, table_present=True, missing=not column)


def format_report(report: VersionColumnReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return [f"{REPORT_PREFIX}: not Postgres, nothing to do"]
    if not report.table_present:
        return [f"{REPORT_PREFIX}: no {USERS_TABLE} table yet, nothing to do"]
    if report.missing:
        return [f"{REPORT_PREFIX}: MISSING {VERSION_COLUMN}"]
    return [f"{REPORT_PREFIX}: {'added' if report.added else 'present'}"]
