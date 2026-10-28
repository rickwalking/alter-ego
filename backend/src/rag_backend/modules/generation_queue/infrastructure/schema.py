"""Deploy one-shot for the queue schema: ``generation_runs`` and PgQueuer's tables.

Prod does not run Alembic, so this is the authoritative way the queue's tables
reach prod (palette_timestamptz pattern). The ``generation_runs`` DDL is compiled
from the ORM table, which the Alembic revision mirrors (the schema-drift gate
compares the two), so the three can never disagree. ``CREATE ... IF NOT EXISTS``
and PgQueuer's own ``upgrade`` (applies only missing pieces) make a second run a
no-op. A database that is not Postgres is a no-op.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import structlog
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from sqlalchemy import Index, Table, text
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.schema import CreateIndex, CreateTable

from rag_backend.modules.generation_queue.constants import (
    TABLE_CAROUSEL_GENERATION_EVENTS,
    TABLE_GENERATION_RUNS,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    asyncpg_connection,
)

logger = structlog.get_logger()

POSTGRES_DIALECT = "postgresql"
LOG_APPLIED = "generation_queue_schema_applied"
LOG_VERIFIED = "generation_queue_schema_verified"

_TABLE_EXISTS_SQL = text(
    "SELECT 1 FROM information_schema.tables"
    " WHERE table_schema = current_schema() AND table_name = :table"
)
_INDEX_EXISTS_SQL = text(
    "SELECT 1 FROM pg_indexes"
    " WHERE schemaname = current_schema() AND indexname = :index"
)


def _table() -> Table:
    return cast(Table, GenerationRunModel.__table__)


def _indexes() -> list[Index]:
    return sorted(_table().indexes, key=lambda index: str(index.name))


def generation_runs_ddl(dialect: Dialect) -> list[str]:
    """The ``generation_runs`` DDL for ``dialect``, compiled from the ORM table."""
    return _model_ddl(_table(), _indexes(), dialect)


def _register_foreign_key_targets() -> str:
    """Attach the tables the events foreign keys point at to the shared metadata.

    The deploy process loads no other model, so without this the events DDL
    cannot resolve ``carousel_projects``. Imported lazily: the shared model
    package imports this module's package.
    """
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    return CarouselProjectModel.__tablename__


def generation_events_ddl(dialect: Dialect) -> list[str]:
    """The generation-event DDL compiled from the same ORM as Alembic."""
    _register_foreign_key_targets()
    table = cast(Table, CarouselGenerationEventModel.__table__)
    indexes = sorted(table.indexes, key=lambda index: str(index.name))
    return _model_ddl(table, indexes, dialect)


def _model_ddl(table: Table, indexes: list[Index], dialect: Dialect) -> list[str]:
    statements = [str(CreateTable(table, if_not_exists=True).compile(dialect=dialect))]
    statements += [
        str(CreateIndex(index, if_not_exists=True).compile(dialect=dialect))
        for index in indexes
    ]
    return statements


@dataclass(frozen=True)
class QueueSchemaReport:
    """What one run found and did."""

    supported: bool
    created: tuple[str, ...] = ()
    pgqueuer: str = ""
    missing: tuple[str, ...] = ()


async def _missing_objects(conn: AsyncConnection) -> tuple[str, ...]:
    event_table = cast(Table, CarouselGenerationEventModel.__table__)
    event_indexes = sorted(event_table.indexes, key=lambda index: str(index.name))
    missing = await _missing_model(conn, TABLE_GENERATION_RUNS, _indexes())
    missing += await _missing_model(
        conn, TABLE_CAROUSEL_GENERATION_EVENTS, event_indexes
    )
    return tuple(missing)


async def _missing_model(
    conn: AsyncConnection, table_name: str, indexes: list[Index]
) -> list[str]:
    missing: list[str] = []
    found = await conn.execute(_TABLE_EXISTS_SQL, {"table": table_name})
    if found.first() is None:
        missing.append(table_name)
    for index in indexes:
        row = await conn.execute(_INDEX_EXISTS_SQL, {"index": str(index.name)})
        if row.first() is None:
            missing.append(str(index.name))
    return missing


async def _pgqueuer_install(engine: AsyncEngine) -> str:
    """``install`` on a fresh database, ``upgrade`` on an installed one."""
    async with asyncpg_connection(engine) as connection:
        queries = Queries(AsyncpgDriver(connection))
        if not await queries.schema_is_installed():
            await queries.install()
            return "installed"
        plan = await queries.apply_upgrade()
        return f"upgraded ({len(plan.statements)} statements)"


async def _pgqueuer_missing(engine: AsyncEngine) -> tuple[str, ...]:
    async with asyncpg_connection(engine) as connection:
        queries = Queries(AsyncpgDriver(connection))
        settings = queries.qbe.settings
        tables = (
            settings.queue_table,
            settings.queue_table_log,
            settings.statistics_table,
            settings.schedules_table,
        )
        missing = [table for table in tables if not await queries.has_table(table)]
        return tuple(missing)


async def apply(engine: AsyncEngine) -> QueueSchemaReport:
    """Create what is missing; upgrade PgQueuer."""
    if engine.dialect.name != POSTGRES_DIALECT:
        return QueueSchemaReport(supported=False)
    async with engine.begin() as conn:
        missing = await _missing_objects(conn)
        statements = generation_runs_ddl(engine.dialect)
        statements += generation_events_ddl(engine.dialect)
        for statement in statements:
            await conn.execute(text(statement))
    pgqueuer = await _pgqueuer_install(engine)
    logger.info(LOG_APPLIED, created=list(missing), pgqueuer=pgqueuer)
    return QueueSchemaReport(supported=True, created=missing, pgqueuer=pgqueuer)


async def verify(engine: AsyncEngine) -> QueueSchemaReport:
    """Report every queue object still missing."""
    if engine.dialect.name != POSTGRES_DIALECT:
        return QueueSchemaReport(supported=False)
    async with engine.connect() as conn:
        missing = await _missing_objects(conn)
    missing += await _pgqueuer_missing(engine)
    logger.info(LOG_VERIFIED, missing=list(missing))
    return QueueSchemaReport(supported=True, missing=missing)


def format_report(report: QueueSchemaReport) -> list[str]:
    """Human-readable lines for the deploy log."""
    if not report.supported:
        return ["generation queue schema: not Postgres, nothing to do"]
    lines: list[str] = []
    if report.pgqueuer:
        created = ", ".join(report.created) or "none"
        lines.append(f"generation queue schema: created {created}")
        lines.append(f"generation queue schema: pgqueuer {report.pgqueuer}")
    if report.missing:
        lines.append(f"generation queue schema: MISSING {', '.join(report.missing)}")
    if not lines:
        lines.append("generation queue schema: all present")
    return lines


__all__ = [
    "QueueSchemaReport",
    "apply",
    "format_report",
    "generation_events_ddl",
    "generation_runs_ddl",
    "verify",
]
