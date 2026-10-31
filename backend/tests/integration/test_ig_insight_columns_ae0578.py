"""The Instagram insight columns one-shot on Postgres."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import ig_insight_columns
from rag_backend.scripts.ig_insight_columns import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_INSIGHTS_SQL = text(
    "CREATE TABLE instagram_post_insights (media_id VARCHAR(128) PRIMARY KEY,"
    " views INTEGER, reach INTEGER, fetched_at TIMESTAMPTZ NOT NULL)"
)
_SEED_SQL = text(
    "INSERT INTO instagram_post_insights (media_id, views, reach, fetched_at)"
    " VALUES ('m1', 120, 80, '2026-10-30T12:00:00Z')"
)
_COLUMNS_SQL = text(
    "SELECT column_name, data_type, is_nullable FROM information_schema.columns"
    " WHERE table_schema = current_schema()"
    " AND table_name = 'instagram_post_insights'"
)
_ROWS_SQL = text(
    "SELECT media_id, views, reach, likes, comments, avg_watch_time_ms,"
    " total_watch_time_ms FROM instagram_post_insights"
)


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _insights_without_new_columns() -> AsyncIterator[AsyncEngine]:
    """An instagram_post_insights table shaped like prod before the fix."""
    async with isolated_schema([]) as engine:
        async with engine.begin() as conn:
            await conn.execute(_INSIGHTS_SQL)
            await conn.execute(_SEED_SQL)
        yield engine


async def _columns(engine: AsyncEngine) -> dict[str, tuple[str, str]]:
    async with engine.connect() as conn:
        rows = await conn.execute(_COLUMNS_SQL)
        return {str(row[0]): (str(row[1]), str(row[2])) for row in rows}


@requires_postgres
async def test_apply_adds_the_four_columns_once() -> None:
    """Scenario: The four insight columns are added once"""
    async with _insights_without_new_columns() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        columns = await _columns(engine)
        async with engine.connect() as conn:
            rows = [tuple(row) for row in await conn.execute(_ROWS_SQL)]

    assert code == EXIT_OK
    for name in ig_insight_columns.INSIGHT_COLUMNS:
        assert columns[name] == ("integer", "YES")
    assert rows == [("m1", 120, 80, None, None, None, None)]


@requires_postgres
async def test_second_apply_changes_nothing() -> None:
    """Scenario: A second insight columns run changes nothing"""
    async with _insights_without_new_columns() as engine:
        first = await ig_insight_columns.apply(engine)
        second = await ig_insight_columns.apply(engine)
        verified = await ig_insight_columns.verify(engine)

    assert first.added == ig_insight_columns.INSIGHT_COLUMNS
    assert second.added == ()
    assert ig_insight_columns.format_report(second) == [
        "ig insight columns: added none (present)"
    ]
    assert verified.missing == ()


@requires_postgres
async def test_verify_fails_while_a_column_is_missing() -> None:
    """Scenario: Verify fails while an insight column is missing"""
    async with _insights_without_new_columns() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await ig_insight_columns.verify(engine)
        columns = await _columns(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.missing == ig_insight_columns.INSIGHT_COLUMNS
    assert ig_insight_columns.format_report(report)[-1] == (
        "ig insight columns: MISSING likes, comments, avg_watch_time_ms,"
        " total_watch_time_ms"
    )
    assert "likes" not in columns


@requires_postgres
async def test_a_database_without_the_table_is_left_alone() -> None:
    """Scenario: A database without the insights table is left alone"""
    async with isolated_schema([]) as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        report = await ig_insight_columns.apply(engine)
        columns = await _columns(engine)

    assert code == EXIT_OK
    assert report == ig_insight_columns.InsightColumnsReport(supported=True)
    assert columns == {}


@requires_postgres
async def test_apply_only_adds_the_columns_and_exits_0() -> None:
    """Scenario: The four insight columns are added once"""
    async with _insights_without_new_columns() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=False))
        report = await ig_insight_columns.verify(engine)

    assert code == EXIT_OK
    assert report.missing == ()
