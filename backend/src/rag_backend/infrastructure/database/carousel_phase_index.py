"""Create the ``carousel_projects (phase_status, current_phase)`` index in prod.

Prod does not run Alembic on deploy and bootstraps with ``create_all``, which
never adds an index to an existing table. So the index that revision
``f7a8b9c0d1e2`` creates for fresh databases reaches prod through this
idempotent one-shot, run by the deploy right after the palette timestamptz step,
the same pattern.

``CREATE INDEX CONCURRENTLY`` cannot run inside a transaction, so it runs on an
autocommit connection. A concurrent build that failed leaves an INVALID index
that ``IF NOT EXISTS`` would keep forever; ``apply`` drops such an index first
and builds it again. A database that is not Postgres (SQLite in tests) is a
no-op.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = structlog.get_logger(__name__)

PHASE_INDEX_NAME = "idx_carousel_projects_phase_status_current_phase"
POSTGRES_DIALECT = "postgresql"
AUTOCOMMIT = "AUTOCOMMIT"
LOG_SKIPPED = "carousel_phase_index_skipped"
LOG_APPLIED = "carousel_phase_index_applied"
LOG_VERIFIED = "carousel_phase_index_verified"

_STATE_SQL = text(
    "SELECT i.indisvalid FROM pg_index i"
    " JOIN pg_class c ON c.oid = i.indexrelid"
    " JOIN pg_namespace n ON n.oid = c.relnamespace"
    " WHERE c.relname = :name AND n.nspname = current_schema()"
)
_DROP_SQL = text(f"DROP INDEX CONCURRENTLY IF EXISTS {PHASE_INDEX_NAME}")
_CREATE_SQL = text(
    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {PHASE_INDEX_NAME}"
    " ON carousel_projects (phase_status, current_phase)"
)


@dataclass(frozen=True)
class PhaseIndexReport:
    """What one run found and did."""

    supported: bool
    created: bool = False
    rebuilt_invalid: bool = False
    present: bool = False


def is_supported(engine: AsyncEngine) -> bool:
    """Only Postgres runs the one-shot."""
    return engine.dialect.name == POSTGRES_DIALECT


async def _index_state(conn: AsyncConnection) -> bool | None:
    """True valid, False invalid, None missing."""
    valid = await conn.scalar(_STATE_SQL, {"name": PHASE_INDEX_NAME})
    return None if valid is None else bool(valid)


async def apply(engine: AsyncEngine) -> PhaseIndexReport:
    """Build the index unless a valid one exists; rebuild an invalid one."""
    if not is_supported(engine):
        logger.info(LOG_SKIPPED, dialect=engine.dialect.name)
        return PhaseIndexReport(supported=False)
    async with engine.connect() as base:
        conn = await base.execution_options(isolation_level=AUTOCOMMIT)
        state = await _index_state(conn)
        if state is False:
            await conn.execute(_DROP_SQL)
        if state is not True:
            await conn.execute(_CREATE_SQL)
    report = PhaseIndexReport(
        supported=True,
        created=state is not True,
        rebuilt_invalid=state is False,
        present=True,
    )
    logger.info(
        LOG_APPLIED,
        created=report.created,
        rebuilt_invalid=report.rebuilt_invalid,
    )
    return report


async def verify(engine: AsyncEngine) -> PhaseIndexReport:
    """Report whether a valid index is present."""
    if not is_supported(engine):
        logger.info(LOG_SKIPPED, dialect=engine.dialect.name)
        return PhaseIndexReport(supported=False)
    async with engine.connect() as conn:
        present = await _index_state(conn) is True
    logger.info(LOG_VERIFIED, present=present)
    return PhaseIndexReport(supported=True, present=present)


def format_report(report: PhaseIndexReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return ["carousel phase index: not Postgres, nothing to do"]
    if report.rebuilt_invalid:
        return [f"carousel phase index: rebuilt invalid {PHASE_INDEX_NAME}"]
    if report.created:
        return [f"carousel phase index: created {PHASE_INDEX_NAME}"]
    if report.present:
        return [f"carousel phase index: {PHASE_INDEX_NAME} present and valid"]
    return [f"carousel phase index: {PHASE_INDEX_NAME} MISSING"]
