"""Add the four Instagram insight columns on prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds a column to an existing table. ``create_all`` created the new
``ig_media`` table of revision ``f9a0b1c2d3e4`` but not its four nullable
columns on the existing ``instagram_post_insights`` table, so the insights read
failed with a database error. Those columns reach prod through this idempotent
one-shot instead, run by the deploy after the generation queue schema step.
A short lock timeout makes a hand run with the stack up fail fast instead of
queueing every insights read behind the ``ALTER``.

``ADD COLUMN IF NOT EXISTS`` makes a second run a no-op. A database without the
table yet is left alone (``create_all`` creates it with every column), and a
database that is not Postgres (SQLite in tests) is a no-op. The SQL is fixed
text, never built from input.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

INSIGHTS_TABLE = "instagram_post_insights"
INSIGHT_COLUMNS = (
    "likes",
    "comments",
    "avg_watch_time_ms",
    "total_watch_time_ms",
)
POSTGRES_DIALECT = "postgresql"
REPORT_PREFIX = "ig insight columns"

_TABLE_EXISTS_SQL = text(
    "SELECT 1 FROM information_schema.tables"
    " WHERE table_schema = current_schema() AND table_name = :table"
)
_COLUMNS_SQL = text(
    "SELECT column_name FROM information_schema.columns"
    " WHERE table_schema = current_schema() AND table_name = :table"
)
_LOCK_TIMEOUT_SQL = text("SET LOCAL lock_timeout = '5s'")
_ADD_COLUMN_SQL = {
    column: text(
        f"ALTER TABLE {INSIGHTS_TABLE} ADD COLUMN IF NOT EXISTS {column} INTEGER NULL"
    )
    for column in INSIGHT_COLUMNS
}


@dataclass(frozen=True)
class InsightColumnsReport:
    """What one run found and did."""

    supported: bool
    table_present: bool = False
    added: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


def is_supported(engine: AsyncEngine) -> bool:
    """Only Postgres is bootstrapped without Alembic."""
    return engine.dialect.name == POSTGRES_DIALECT


async def _table_present(conn: AsyncConnection) -> bool:
    found = await conn.execute(_TABLE_EXISTS_SQL, {"table": INSIGHTS_TABLE})
    return found.first() is not None


async def _missing(conn: AsyncConnection) -> tuple[str, ...]:
    """The insight columns the existing table does not have yet."""
    rows = await conn.execute(_COLUMNS_SQL, {"table": INSIGHTS_TABLE})
    present = {str(row[0]) for row in rows}
    return tuple(column for column in INSIGHT_COLUMNS if column not in present)


def _skipped(engine: AsyncEngine) -> InsightColumnsReport:
    logger.info("ig_insight_columns_skipped", dialect=engine.dialect.name)
    return InsightColumnsReport(supported=False)


async def apply(engine: AsyncEngine) -> InsightColumnsReport:
    """Add the missing nullable columns to an existing table (one transaction)."""
    if not is_supported(engine):
        return _skipped(engine)
    async with engine.begin() as conn:
        if not await _table_present(conn):
            logger.info("ig_insight_columns_no_table")
            return InsightColumnsReport(supported=True)
        missing = await _missing(conn)
        await conn.execute(_LOCK_TIMEOUT_SQL)
        for column in missing:
            await conn.execute(_ADD_COLUMN_SQL[column])
    logger.info("ig_insight_columns_applied", added=list(missing))
    return InsightColumnsReport(supported=True, table_present=True, added=missing)


async def verify(engine: AsyncEngine) -> InsightColumnsReport:
    """Report the columns an existing table still lacks."""
    if not is_supported(engine):
        return _skipped(engine)
    async with engine.connect() as conn:
        if not await _table_present(conn):
            return InsightColumnsReport(supported=True)
        missing = await _missing(conn)
    logger.info("ig_insight_columns_verified", missing=list(missing))
    return InsightColumnsReport(supported=True, table_present=True, missing=missing)


def format_report(report: InsightColumnsReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return [f"{REPORT_PREFIX}: not Postgres, nothing to do"]
    if not report.table_present:
        return [f"{REPORT_PREFIX}: no {INSIGHTS_TABLE} table yet, nothing to do"]
    lines = [f"{REPORT_PREFIX}: added {', '.join(report.added) or 'none (present)'}"]
    if report.missing:
        lines.append(f"{REPORT_PREFIX}: MISSING {', '.join(report.missing)}")
    return lines
