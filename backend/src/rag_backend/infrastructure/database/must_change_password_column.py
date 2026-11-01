"""Add ``users.must_change_password`` on prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds a column to an existing table. So the column that revision
``b9c0d1e2f3a4`` adds for fresh databases reaches prod through this idempotent
one-shot instead, run by the deploy after the insight columns step.

The column is ``BOOLEAN NOT NULL DEFAULT false``: Postgres 11+ keeps a constant
default in the catalog, so existing rows read false without a table rewrite.
A short lock timeout makes a hand run with the stack up fail fast instead of
queueing every sign-in behind the ``ALTER``. ``ADD COLUMN IF NOT EXISTS`` makes
a second run a no-op; a database without ``users`` yet is left alone
(``create_all`` creates it with the column), and a database that is not
Postgres (SQLite in tests) is a no-op. The SQL is fixed text, never built from
input.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

USERS_TABLE = "users"
FLAG_COLUMN = "must_change_password"
POSTGRES_DIALECT = "postgresql"
REPORT_PREFIX = "users must_change_password"

_USERS_TABLE_SQL = text(
    "SELECT 1 FROM information_schema.tables"
    " WHERE table_schema = current_schema() AND table_name = :table"
)
_FLAG_COLUMN_SQL = text(
    "SELECT 1 FROM information_schema.columns"
    " WHERE table_schema = current_schema()"
    " AND table_name = :table AND column_name = :column"
)
_FAIL_FAST_SQL = text("SET LOCAL lock_timeout = '5s'")
_ADD_FLAG_SQL = text(
    f"ALTER TABLE {USERS_TABLE} ADD COLUMN IF NOT EXISTS {FLAG_COLUMN}"
    " BOOLEAN NOT NULL DEFAULT false"
)


@dataclass(frozen=True)
class FlagColumnReport:
    """What one run found and did."""

    supported: bool
    table_present: bool = False
    added: bool = False
    missing: bool = False


async def _has_users(conn: AsyncConnection) -> bool:
    found = await conn.execute(_USERS_TABLE_SQL, {"table": USERS_TABLE})
    return found.first() is not None


async def _has_flag(conn: AsyncConnection) -> bool:
    found = await conn.execute(
        _FLAG_COLUMN_SQL, {"table": USERS_TABLE, "column": FLAG_COLUMN}
    )
    return found.first() is not None


def _not_postgres(engine: AsyncEngine) -> FlagColumnReport | None:
    """The skip report outside Postgres, else ``None``."""
    if engine.dialect.name == POSTGRES_DIALECT:
        return None
    logger.info("must_change_password_column_skipped", dialect=engine.dialect.name)
    return FlagColumnReport(supported=False)


async def apply(engine: AsyncEngine) -> FlagColumnReport:
    """Add the column to an existing ``users`` table (one transaction)."""
    skipped = _not_postgres(engine)
    if skipped is not None:
        return skipped
    async with engine.begin() as conn:
        if not await _has_users(conn):
            return FlagColumnReport(supported=True)
        present = await _has_flag(conn)
        await conn.execute(_FAIL_FAST_SQL)
        await conn.execute(_ADD_FLAG_SQL)
    logger.info("must_change_password_column_applied", added=not present)
    return FlagColumnReport(supported=True, table_present=True, added=not present)


async def verify(engine: AsyncEngine) -> FlagColumnReport:
    """Report whether an existing ``users`` table still lacks the column."""
    skipped = _not_postgres(engine)
    if skipped is not None:
        return skipped
    async with engine.connect() as conn:
        if not await _has_users(conn):
            return FlagColumnReport(supported=True)
        missing = not await _has_flag(conn)
    logger.info("must_change_password_column_verified", missing=missing)
    return FlagColumnReport(supported=True, table_present=True, missing=missing)


def format_report(report: FlagColumnReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return [f"{REPORT_PREFIX}: not Postgres, nothing to do"]
    if not report.table_present:
        return [f"{REPORT_PREFIX}: no {USERS_TABLE} table yet, nothing to do"]
    if report.missing:
        return [f"{REPORT_PREFIX}: MISSING {FLAG_COLUMN}"]
    return [f"{REPORT_PREFIX}: {'added' if report.added else 'present'}"]
