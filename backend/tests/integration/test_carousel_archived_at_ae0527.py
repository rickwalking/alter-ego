"""The carousel archived_at one-shot on Postgres, and its Alembic revision."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import carousel_archived_at
from rag_backend.scripts.carousel_archived_at import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_migration import ALEMBIC_HEAD, _alembic_config

_REVISION = "aa4a5695681f"
_PARENT = "c7d8e9f0a1b3"
_PROJECTS_SQL = text(
    "CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY,"
    " current_phase VARCHAR(50), phase_status VARCHAR(50))"
)
_SEED_SQL = text(
    "INSERT INTO carousel_projects (id, current_phase) VALUES ('p1', 'research')"
)
_COLUMN_SQL = text(
    "SELECT data_type, is_nullable FROM information_schema.columns"
    " WHERE table_schema = current_schema() AND table_name = 'carousel_projects'"
    " AND column_name = 'archived_at'"
)
_INDEX_SQL = text(
    "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
    " AND indexname = 'idx_carousel_projects_archived_at'"
)
_ROWS_SQL = text("SELECT id, current_phase, archived_at FROM carousel_projects")


def test_revision_sits_on_top_of_the_content_versions_index() -> None:
    """Scenario: The column and its index are added once"""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [ALEMBIC_HEAD]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _projects_without_archived_at() -> AsyncIterator[AsyncEngine]:
    """A carousel_projects table shaped like prod today: no archived_at."""
    async with isolated_schema([]) as engine:
        async with engine.begin() as conn:
            await conn.execute(_PROJECTS_SQL)
            await conn.execute(_SEED_SQL)
        yield engine


async def _column(engine: AsyncEngine) -> tuple[str, str] | None:
    async with engine.connect() as conn:
        row = (await conn.execute(_COLUMN_SQL)).first()
    return None if row is None else (str(row[0]), str(row[1]))


async def _has_index(engine: AsyncEngine) -> bool:
    async with engine.connect() as conn:
        return (await conn.execute(_INDEX_SQL)).first() is not None


@requires_postgres
async def test_apply_adds_the_column_and_index_once() -> None:
    """Scenario: The column and its index are added once"""
    async with _projects_without_archived_at() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        column = await _column(engine)
        indexed = await _has_index(engine)
        async with engine.connect() as conn:
            rows = list(await conn.execute(_ROWS_SQL))

    assert code == EXIT_OK
    assert column == ("timestamp with time zone", "YES")
    assert indexed
    assert [(row[0], row[1], row[2]) for row in rows] == [("p1", "research", None)]


@requires_postgres
async def test_second_apply_changes_nothing() -> None:
    """Scenario: A second run changes nothing"""
    async with _projects_without_archived_at() as engine:
        first = await carousel_archived_at.apply(engine)
        second = await carousel_archived_at.apply(engine)
        verified = await carousel_archived_at.verify(engine)

    assert (first.column_added, first.index_added) == (True, True)
    assert (second.column_added, second.index_added) == (False, False)
    assert carousel_archived_at.format_report(second) == [
        "carousel archived_at: added none (present)"
    ]
    assert verified.missing == ()


@requires_postgres
async def test_verify_fails_while_the_column_is_missing() -> None:
    """Scenario: Verify fails while the column is missing"""
    async with _projects_without_archived_at() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await carousel_archived_at.verify(engine)
        column = await _column(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.missing == (
        carousel_archived_at.ARCHIVED_AT_COLUMN,
        carousel_archived_at.ARCHIVED_AT_INDEX,
    )
    assert carousel_archived_at.format_report(report)[-1] == (
        "carousel archived_at: MISSING archived_at, idx_carousel_projects_archived_at"
    )
    assert column is None
