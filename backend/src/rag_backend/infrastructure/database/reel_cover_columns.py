"""Add the reel cover columns to ``autopilot_cover_assets`` on prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds a column to an existing table. ``create_all`` created the two new
repost tables of revision ``c3d4e5f6a7b9`` but not ``purpose`` and
``repost_id`` on the existing cover table, so every read of a cover asset
failed. Those columns reach prod through this idempotent one-shot instead, run
by the deploy after the token version step.

``purpose`` is ``VARCHAR(16) NOT NULL DEFAULT 'carousel_cover'``: Postgres 11+
keeps a constant default in the catalog, so existing rows read as carousel
covers without a table rewrite. ``repost_id`` is a nullable UUID. A short lock
timeout makes a hand run with the stack up fail fast. ``ADD COLUMN IF NOT
EXISTS`` makes a second run a no-op. A database without the table yet is left
alone (``create_all`` creates it with every column), and a database that is
not Postgres (SQLite in tests) is a no-op. The SQL is fixed text, never built
from input.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

COVERS_TABLE = "autopilot_cover_assets"
PURPOSE_COLUMN = "purpose"
REPOST_COLUMN = "repost_id"
PURPOSE_DEFAULT = "carousel_cover"
COLUMN_DDL = {
    PURPOSE_COLUMN: f"VARCHAR(16) NOT NULL DEFAULT '{PURPOSE_DEFAULT}'",
    REPOST_COLUMN: "UUID NULL",
}
POSTGRES_DIALECT = "postgresql"
REPORT_PREFIX = "reel cover columns"

_PRESENT_SQL = text(
    "SELECT column_name FROM information_schema.columns"
    " WHERE table_schema = current_schema() AND table_name = :table"
)
_LOCK_TIMEOUT_SQL = text("SET LOCAL lock_timeout = '5s'")
_ADD_SQL: dict[str, TextClause] = {
    name: text(f"ALTER TABLE {COVERS_TABLE} ADD COLUMN IF NOT EXISTS {name} {ddl}")
    for name, ddl in COLUMN_DDL.items()
}


@dataclass(frozen=True)
class CoverColumnsReport:
    """What one run found and did."""

    supported: bool
    table_present: bool = False
    added: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


async def _absent(conn: AsyncConnection) -> tuple[str, ...] | None:
    """The cover columns still absent; None when the table does not exist."""
    rows = await conn.execute(_PRESENT_SQL, {"table": COVERS_TABLE})
    present = {str(row[0]) for row in rows}
    if not present:
        return None
    return tuple(name for name in COLUMN_DDL if name not in present)


def _postgres(engine: AsyncEngine) -> bool:
    if engine.dialect.name == POSTGRES_DIALECT:
        return True
    logger.info("reel_cover_columns_skipped", dialect=engine.dialect.name)
    return False


async def apply(engine: AsyncEngine) -> CoverColumnsReport:
    """Add the absent columns to an existing cover table (one transaction)."""
    if not _postgres(engine):
        return CoverColumnsReport(supported=False)
    async with engine.begin() as conn:
        absent = await _absent(conn)
        if absent is None:
            return CoverColumnsReport(supported=True)
        if absent:
            await conn.execute(_LOCK_TIMEOUT_SQL)
        for name in absent:
            await conn.execute(_ADD_SQL[name])
    logger.info("reel_cover_columns_applied", added=list(absent))
    return CoverColumnsReport(supported=True, table_present=True, added=absent)


async def verify(engine: AsyncEngine) -> CoverColumnsReport:
    """Report the columns an existing cover table still lacks."""
    if not _postgres(engine):
        return CoverColumnsReport(supported=False)
    async with engine.connect() as conn:
        absent = await _absent(conn)
    if absent is None:
        return CoverColumnsReport(supported=True)
    logger.info("reel_cover_columns_verified", missing=list(absent))
    return CoverColumnsReport(supported=True, table_present=True, missing=absent)


def format_report(report: CoverColumnsReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return [f"{REPORT_PREFIX}: not Postgres, nothing to do"]
    if not report.table_present:
        return [f"{REPORT_PREFIX}: no {COVERS_TABLE} table yet, nothing to do"]
    if report.missing:
        return [f"{REPORT_PREFIX}: MISSING {', '.join(report.missing)}"]
    return [f"{REPORT_PREFIX}: added {', '.join(report.added) or 'none (present)'}"]
