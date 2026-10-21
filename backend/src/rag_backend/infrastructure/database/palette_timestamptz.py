"""Make the ``palettes`` timestamps timezone-aware (Pedro's decision).

Prod does not run Alembic on deploy and bootstraps with
``create_all``, which never alters an existing column. So the
``timestamp`` -> ``timestamptz`` change that revision ``e6f7a8b9c0d1`` makes
for fresh databases reaches prod through this idempotent one-shot instead,
run by the deploy right after the blog cutover, the same pattern.

The stored naive values were written as UTC, so they are converted with
``AT TIME ZONE 'UTC'`` (the instant is unchanged). Both columns change in one
transaction; a column that is already ``timestamptz`` is left alone, and a
database that is not Postgres (SQLite in tests) is a no-op.

The ALTER statements interpolate column names only from the fixed column tuple, never
from input.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

PALETTES_TABLE = "palettes"
PALETTE_TIMESTAMP_COLUMNS = ("created_at", "updated_at")
NAIVE_TIMESTAMP_TYPE = "timestamp without time zone"
POSTGRES_DIALECT = "postgresql"

_NAIVE_COLUMNS_SQL = text(
    "SELECT column_name FROM information_schema.columns"
    " WHERE table_schema = current_schema()"
    " AND table_name = :table AND data_type = :naive"
    " ORDER BY column_name"
)
_ALTER_SQL = {
    column: text(
        f"ALTER TABLE {PALETTES_TABLE} ALTER COLUMN {column}"
        f" TYPE timestamptz USING {column} AT TIME ZONE 'UTC'"
    )
    for column in PALETTE_TIMESTAMP_COLUMNS
}


@dataclass(frozen=True)
class TimestamptzReport:
    """What one run found and did."""

    supported: bool
    altered: tuple[str, ...] = ()
    still_naive: tuple[str, ...] = ()


def is_supported(engine: AsyncEngine) -> bool:
    """Only Postgres has a naive/aware split to fix."""
    return engine.dialect.name == POSTGRES_DIALECT


async def _naive_columns(conn: AsyncConnection) -> tuple[str, ...]:
    result = await conn.execute(
        _NAIVE_COLUMNS_SQL,
        {"table": PALETTES_TABLE, "naive": NAIVE_TIMESTAMP_TYPE},
    )
    return tuple(str(row[0]) for row in result)


async def apply(engine: AsyncEngine) -> TimestamptzReport:
    """ALTER the palette timestamps that are still naive (one transaction)."""
    if not is_supported(engine):
        logger.info("palette_timestamptz_skipped", dialect=engine.dialect.name)
        return TimestamptzReport(supported=False)
    async with engine.begin() as conn:
        naive = await _naive_columns(conn)
        altered = tuple(c for c in PALETTE_TIMESTAMP_COLUMNS if c in naive)
        for column in altered:
            await conn.execute(_ALTER_SQL[column])
    logger.info("palette_timestamptz_applied", altered=list(altered))
    return TimestamptzReport(supported=True, altered=altered)


async def verify(engine: AsyncEngine) -> TimestamptzReport:
    """Report every ``palettes`` column that is still a naive timestamp."""
    if not is_supported(engine):
        logger.info("palette_timestamptz_skipped", dialect=engine.dialect.name)
        return TimestamptzReport(supported=False)
    async with engine.connect() as conn:
        naive = await _naive_columns(conn)
    logger.info("palette_timestamptz_verified", still_naive=list(naive))
    return TimestamptzReport(supported=True, still_naive=naive)


def format_report(report: TimestamptzReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return ["palette timestamptz: not Postgres, nothing to do"]
    altered = ", ".join(report.altered) or "none (already timestamptz)"
    lines = [f"palette timestamptz: altered {altered}"]
    if report.still_naive:
        lines.append(
            f"palette timestamptz: STILL NAIVE {', '.join(report.still_naive)}"
        )
    return lines
