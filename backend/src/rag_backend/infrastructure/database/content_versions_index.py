"""Make the ``content_versions`` unique index per content (Pedro's decision).

The table's unique index was global on ``(content_type, version_number)``: two
carousels could not both have a version 1, so it could not hold per-carousel
histories. Revision ``c7d8e9f0a1b3`` replaces it with a unique index on
``(content_id, content_type, version_number)`` for fresh databases. Prod does
not run Alembic on deploy and bootstraps with ``create_all``, which never
changes an existing index, so the change reaches prod through this idempotent
one-shot, run by the deploy right after the blog cutover (the palette
timestamptz pattern).

The old index is dropped if present and the new one created if absent, in one
transaction. The old index was stricter, so no existing rows can break the new
one. A database that is not Postgres (SQLite in tests) is a no-op.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

CONTENT_VERSIONS_TABLE = "content_versions"
GLOBAL_INDEX = "idx_content_versions_version"
PER_CONTENT_INDEX = "uq_content_versions_content_version"
POSTGRES_DIALECT = "postgresql"

_INDEXES_SQL = text(
    "SELECT indexname FROM pg_indexes"
    " WHERE schemaname = current_schema() AND tablename = :table"
)
_DROP_GLOBAL_SQL = text(f"DROP INDEX IF EXISTS {GLOBAL_INDEX}")
_CREATE_PER_CONTENT_SQL = text(
    f"CREATE UNIQUE INDEX IF NOT EXISTS {PER_CONTENT_INDEX}"
    f" ON {CONTENT_VERSIONS_TABLE} (content_id, content_type, version_number)"
)


@dataclass(frozen=True)
class IndexReport:
    """What one run found and did."""

    supported: bool
    dropped_global: bool = False
    created_per_content: bool = False
    global_present: bool = False
    per_content_present: bool = False


def is_supported(engine: AsyncEngine) -> bool:
    """Only Postgres carries the prod schema to fix."""
    return engine.dialect.name == POSTGRES_DIALECT


async def _indexes(conn: AsyncConnection) -> set[str]:
    result = await conn.execute(_INDEXES_SQL, {"table": CONTENT_VERSIONS_TABLE})
    return {str(row[0]) for row in result}


async def apply(engine: AsyncEngine) -> IndexReport:
    """Drop the global index and create the per-content one (one transaction)."""
    if not is_supported(engine):
        logger.info("content_versions_index_skipped", dialect=engine.dialect.name)
        return IndexReport(supported=False)
    async with engine.begin() as conn:
        before = await _indexes(conn)
        await conn.execute(_DROP_GLOBAL_SQL)
        await conn.execute(_CREATE_PER_CONTENT_SQL)
    report = IndexReport(
        supported=True,
        dropped_global=GLOBAL_INDEX in before,
        created_per_content=PER_CONTENT_INDEX not in before,
    )
    logger.info(
        "content_versions_index_applied",
        dropped_global=report.dropped_global,
        created_per_content=report.created_per_content,
    )
    return report


async def verify(engine: AsyncEngine) -> IndexReport:
    """Report whether the global index is gone and the per-content one exists."""
    if not is_supported(engine):
        logger.info("content_versions_index_skipped", dialect=engine.dialect.name)
        return IndexReport(supported=False)
    async with engine.connect() as conn:
        present = await _indexes(conn)
    report = IndexReport(
        supported=True,
        global_present=GLOBAL_INDEX in present,
        per_content_present=PER_CONTENT_INDEX in present,
    )
    logger.info(
        "content_versions_index_verified",
        global_present=report.global_present,
        per_content_present=report.per_content_present,
    )
    return report


def is_fixed(report: IndexReport) -> bool:
    """A verified schema with the per-content index and no global one."""
    return report.per_content_present and not report.global_present


def format_report(report: IndexReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return ["content_versions index: not Postgres, nothing to do"]
    return [
        f"content_versions index: dropped global {report.dropped_global},"
        f" created per-content {report.created_per_content},"
        f" global present {report.global_present},"
        f" per-content present {report.per_content_present}"
    ]
