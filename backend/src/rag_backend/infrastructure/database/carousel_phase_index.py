"""Create the ``carousel_projects (phase_status, current_phase)`` index in prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds an index to an existing table. So the index that revision
``f7a8b9c0d1e2`` creates for fresh databases reaches prod through this
idempotent one-shot, run by the deploy right after the palette timestamptz step,
the same pattern.

The deploy runs it while the app stack is down, so a plain transactional
``CREATE INDEX IF NOT EXISTS`` is enough: nothing writes to the table meanwhile
and a failed build leaves no index behind. A database that is not Postgres
(SQLite in tests) is a no-op.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

PHASE_INDEX_NAME = "idx_carousel_projects_phase_status_current_phase"
POSTGRES_DIALECT = "postgresql"
LOG_SKIPPED = "carousel_phase_index_skipped"
LOG_APPLIED = "carousel_phase_index_applied"
LOG_VERIFIED = "carousel_phase_index_verified"

_STATE_SQL = text(
    "SELECT i.indisvalid FROM pg_index i"
    " JOIN pg_class c ON c.oid = i.indexrelid"
    " JOIN pg_namespace n ON n.oid = c.relnamespace"
    " WHERE c.relname = :name AND n.nspname = current_schema()"
)
_CREATE_SQL = text(
    f"CREATE INDEX IF NOT EXISTS {PHASE_INDEX_NAME}"
    " ON carousel_projects (phase_status, current_phase)"
)


@dataclass(frozen=True)
class PhaseIndexReport:
    """What one run found and did."""

    supported: bool
    created: bool = False
    present: bool = False


def is_supported(engine: AsyncEngine) -> bool:
    """Only Postgres runs the one-shot."""
    return engine.dialect.name == POSTGRES_DIALECT


async def _index_valid(conn: AsyncConnection) -> bool:
    """True when a valid index with the expected name exists."""
    return bool(await conn.scalar(_STATE_SQL, {"name": PHASE_INDEX_NAME}))


async def apply(engine: AsyncEngine) -> PhaseIndexReport:
    """Build the index unless it already exists (one transaction)."""
    if not is_supported(engine):
        logger.info(LOG_SKIPPED, dialect=engine.dialect.name)
        return PhaseIndexReport(supported=False)
    async with engine.begin() as conn:
        existed = await _index_valid(conn)
        if not existed:
            await conn.execute(_CREATE_SQL)
    logger.info(LOG_APPLIED, created=not existed)
    return PhaseIndexReport(supported=True, created=not existed, present=True)


async def verify(engine: AsyncEngine) -> PhaseIndexReport:
    """Report whether a valid index is present."""
    if not is_supported(engine):
        logger.info(LOG_SKIPPED, dialect=engine.dialect.name)
        return PhaseIndexReport(supported=False)
    async with engine.connect() as conn:
        present = await _index_valid(conn)
    logger.info(LOG_VERIFIED, present=present)
    return PhaseIndexReport(supported=True, present=present)


def format_report(report: PhaseIndexReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return ["carousel phase index: not Postgres, nothing to do"]
    if report.created:
        return [f"carousel phase index: created {PHASE_INDEX_NAME}"]
    if report.present:
        return [f"carousel phase index: {PHASE_INDEX_NAME} present and valid"]
    return [f"carousel phase index: {PHASE_INDEX_NAME} MISSING"]
