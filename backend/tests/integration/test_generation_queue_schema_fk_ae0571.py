"""The queue schema one-shot applies and verifies twice on a real Postgres."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.constants import (
    INDEX_EVENT_OCCURRED,
    INDEX_EVENT_PROJECT_OCCURRED,
    INDEX_EVENT_RUN_OCCURRED,
    TABLE_CAROUSEL_GENERATION_EVENTS,
)
from rag_backend.modules.generation_queue.infrastructure import schema
from rag_backend.scripts import generation_queue_schema as cli
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

pytestmark = [pytest.mark.integration, requires_postgres]

_TABLES = (
    "users",
    "persona_profiles",
    "quality_rubrics",
    "carousel_creator_assets",
    "carousel_projects",
    "topic_candidates",
    "autopilot_runs",
    "generation_runs",
)
_APPLY_VERIFY = argparse.Namespace(apply=True, verify=True)
_VERIFY_ONLY = argparse.Namespace(apply=False, verify=True)
_EVENT_INDEXES = sorted((
    INDEX_EVENT_OCCURRED,
    INDEX_EVENT_PROJECT_OCCURRED,
    INDEX_EVENT_RUN_OCCURRED,
))
_FOREIGN_TARGETS_SQL = text(
    "SELECT ccu.table_name FROM information_schema.table_constraints tc"
    " JOIN information_schema.constraint_column_usage ccu"
    " ON tc.constraint_name = ccu.constraint_name"
    " AND tc.constraint_schema = ccu.constraint_schema"
    " WHERE tc.table_schema = current_schema() AND tc.table_name = :table"
    " AND tc.constraint_type = 'FOREIGN KEY'"
)
_INDEXES_SQL = text(
    "SELECT indexname FROM pg_indexes"
    " WHERE schemaname = current_schema() AND tablename = :table"
    " AND indexname LIKE 'ix_%'"
)


@pytest_asyncio.fixture(loop_scope="function")
async def engine() -> AsyncIterator[AsyncEngine]:
    async with isolated_schema(_TABLES) as scoped:
        yield scoped


async def _rows(engine: AsyncEngine, query: TextClause) -> list[str]:
    async with engine.connect() as conn:
        result = await conn.execute(query, {"table": TABLE_CAROUSEL_GENERATION_EVENTS})
        return sorted(str(row[0]) for row in result)


async def test_fresh_database_applies_and_verifies(engine: AsyncEngine) -> None:
    """Scenario: Apply and verify on a fresh database exit 0"""
    code = await cli.run_modes(engine, _APPLY_VERIFY)
    assert code == cli.EXIT_OK
    assert await _rows(engine, _FOREIGN_TARGETS_SQL) == [
        "carousel_projects",
        "generation_runs",
    ]
    assert await _rows(engine, _INDEXES_SQL) == _EVENT_INDEXES


async def test_second_run_is_a_no_op(engine: AsyncEngine) -> None:
    """Scenario: A second apply and verify is a no-op that exits 0"""
    first = await cli.run_modes(engine, _APPLY_VERIFY)
    second = await cli.run_modes(engine, _APPLY_VERIFY)
    report = await schema.verify(engine)
    assert first == cli.EXIT_OK
    assert second == cli.EXIT_OK
    assert report.missing == ()
    assert await _rows(engine, _INDEXES_SQL) == _EVENT_INDEXES


async def test_verify_reports_the_missing_events_table(engine: AsyncEngine) -> None:
    """Scenario: Verify fails when the events table is missing"""
    code = await cli.run_modes(engine, _VERIFY_ONLY)
    report = await schema.verify(engine)
    assert code == cli.EXIT_VERIFY_FAILED
    assert TABLE_CAROUSEL_GENERATION_EVENTS in report.missing
