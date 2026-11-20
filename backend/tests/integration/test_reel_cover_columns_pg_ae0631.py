"""The reel cover columns one-shot on Postgres.

Gherkin: tests/features/reel_cover_columns_oneshot_ae0631.feature. Skipped
unless ``DATABASE_URL`` points at Postgres (CI's backend test job does).
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import reel_cover_columns as columns
from rag_backend.scripts.reel_cover_columns import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_COVERS_SQL = text(
    "CREATE TABLE autopilot_cover_assets (asset_id UUID PRIMARY KEY,"
    " kind VARCHAR(16) NOT NULL)"
)
_SEED_SQL = text(
    "INSERT INTO autopilot_cover_assets (asset_id, kind)"
    " VALUES ('00000000-0000-0000-0000-000000000001', 'ai_image')"
)
_COLUMNS_SQL = text(
    "SELECT column_name, data_type, is_nullable FROM information_schema.columns"
    " WHERE table_schema = current_schema()"
    " AND table_name = 'autopilot_cover_assets'"
)
_ROWS_SQL = text("SELECT kind, purpose, repost_id FROM autopilot_cover_assets")


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _covers_without_reel_columns() -> AsyncIterator[AsyncEngine]:
    """An autopilot_cover_assets table shaped like prod before the fix."""
    async with isolated_schema([]) as engine:
        async with engine.begin() as conn:
            await conn.execute(_COVERS_SQL)
            await conn.execute(_SEED_SQL)
        yield engine


async def _columns(engine: AsyncEngine) -> dict[str, tuple[str, str]]:
    async with engine.connect() as conn:
        rows = await conn.execute(_COLUMNS_SQL)
        return {str(row[0]): (str(row[1]), str(row[2])) for row in rows}


# Scenario: The reel cover columns are added once
@requires_postgres
async def test_apply_adds_both_columns_and_keeps_rows() -> None:
    async with _covers_without_reel_columns() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        found = await _columns(engine)
        async with engine.connect() as conn:
            rows = [tuple(row) for row in await conn.execute(_ROWS_SQL)]

    assert code == EXIT_OK
    assert found["purpose"] == ("character varying", "NO")
    assert found["repost_id"] == ("uuid", "YES")
    assert rows == [("ai_image", "carousel_cover", None)]


# Scenario: A second reel cover columns run changes nothing
@requires_postgres
async def test_second_apply_changes_nothing() -> None:
    async with _covers_without_reel_columns() as engine:
        first = await columns.apply(engine)
        second = await columns.apply(engine)
        verified = await columns.verify(engine)

    assert first.added == ("purpose", "repost_id")
    assert second.added == ()
    assert columns.format_report(second) == ["reel cover columns: added none (present)"]
    assert verified.missing == ()


# Scenario: Verify fails while a reel cover column is missing
@requires_postgres
async def test_verify_fails_while_a_column_is_missing() -> None:
    async with _covers_without_reel_columns() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await columns.verify(engine)
        found = await _columns(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.missing == ("purpose", "repost_id")
    assert columns.format_report(report) == [
        "reel cover columns: MISSING purpose, repost_id"
    ]
    assert "purpose" not in found


# Scenario: A database without the cover table is left alone
@requires_postgres
async def test_a_database_without_the_table_is_left_alone() -> None:
    async with isolated_schema([]) as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        report = await columns.apply(engine)
        found = await _columns(engine)

    assert code == EXIT_OK
    assert report == columns.CoverColumnsReport(supported=True)
    assert found == {}
