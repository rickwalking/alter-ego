"""Add ``carousel_projects.archived_at`` on prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds a column to an existing table. So the column that revision
``aa4a5695681f`` adds for fresh databases reaches prod through this idempotent
one-shot instead, run by the deploy right after the palette timestamptz step.

``ADD COLUMN IF NOT EXISTS`` and ``CREATE INDEX IF NOT EXISTS`` make a second run
a no-op; a database that is not Postgres (SQLite in tests) is a no-op. The SQL
is fixed text, never built from input.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

CAROUSELS_TABLE = "carousel_projects"
ARCHIVED_AT_COLUMN = "archived_at"
ARCHIVED_AT_INDEX = "idx_carousel_projects_archived_at"
POSTGRES_DIALECT = "postgresql"

_COLUMN_EXISTS_SQL = text(
    "SELECT 1 FROM information_schema.columns"
    " WHERE table_schema = current_schema()"
    " AND table_name = :table AND column_name = :column"
)
_INDEX_EXISTS_SQL = text(
    "SELECT 1 FROM pg_indexes"
    " WHERE schemaname = current_schema() AND indexname = :index"
)
_ADD_COLUMN_SQL = text(
    f"ALTER TABLE {CAROUSELS_TABLE}"
    f" ADD COLUMN IF NOT EXISTS {ARCHIVED_AT_COLUMN} TIMESTAMPTZ NULL"
)
_ADD_INDEX_SQL = text(
    f"CREATE INDEX IF NOT EXISTS {ARCHIVED_AT_INDEX}"
    f" ON {CAROUSELS_TABLE} ({ARCHIVED_AT_COLUMN})"
)


@dataclass(frozen=True)
class ArchivedAtReport:
    """What one run found and did."""

    supported: bool
    column_added: bool = False
    index_added: bool = False
    missing: tuple[str, ...] = ()


def is_supported(engine: AsyncEngine) -> bool:
    """Only Postgres is bootstrapped without Alembic."""
    return engine.dialect.name == POSTGRES_DIALECT


async def _missing(conn: AsyncConnection) -> tuple[str, ...]:
    """The column and/or index that do not exist yet."""
    missing: list[str] = []
    column = await conn.execute(
        _COLUMN_EXISTS_SQL,
        {"table": CAROUSELS_TABLE, "column": ARCHIVED_AT_COLUMN},
    )
    if column.first() is None:
        missing.append(ARCHIVED_AT_COLUMN)
    index = await conn.execute(_INDEX_EXISTS_SQL, {"index": ARCHIVED_AT_INDEX})
    if index.first() is None:
        missing.append(ARCHIVED_AT_INDEX)
    return tuple(missing)


async def apply(engine: AsyncEngine) -> ArchivedAtReport:
    """Add the column and its index when missing (one transaction)."""
    if not is_supported(engine):
        logger.info("carousel_archived_at_skipped", dialect=engine.dialect.name)
        return ArchivedAtReport(supported=False)
    async with engine.begin() as conn:
        missing = await _missing(conn)
        await conn.execute(_ADD_COLUMN_SQL)
        await conn.execute(_ADD_INDEX_SQL)
    report = ArchivedAtReport(
        supported=True,
        column_added=ARCHIVED_AT_COLUMN in missing,
        index_added=ARCHIVED_AT_INDEX in missing,
    )
    logger.info(
        "carousel_archived_at_applied",
        column_added=report.column_added,
        index_added=report.index_added,
    )
    return report


async def verify(engine: AsyncEngine) -> ArchivedAtReport:
    """Report the column and/or index that are still missing."""
    if not is_supported(engine):
        logger.info("carousel_archived_at_skipped", dialect=engine.dialect.name)
        return ArchivedAtReport(supported=False)
    async with engine.connect() as conn:
        missing = await _missing(conn)
    logger.info("carousel_archived_at_verified", missing=list(missing))
    return ArchivedAtReport(supported=True, missing=missing)


def format_report(report: ArchivedAtReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return ["carousel archived_at: not Postgres, nothing to do"]
    added = [
        name
        for name, done in (
            (ARCHIVED_AT_COLUMN, report.column_added),
            (ARCHIVED_AT_INDEX, report.index_added),
        )
        if done
    ]
    lines = [f"carousel archived_at: added {', '.join(added) or 'none (present)'}"]
    if report.missing:
        lines.append(f"carousel archived_at: MISSING {', '.join(report.missing)}")
    return lines
