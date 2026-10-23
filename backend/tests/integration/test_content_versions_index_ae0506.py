"""The content_versions unique index one-shot on Postgres (Pedro's decision).

Feature: backend/tests/features/carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import content_versions_index
from rag_backend.scripts.content_versions_index import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_migration import ALEMBIC_HEAD, _alembic_config

_REVISION = "c7d8e9f0a1b3"
_PARENT = "f7a8b9c0d1e2"
_TABLE = "content_versions"
_INDEXES_SQL = text(
    "SELECT indexname FROM pg_indexes"
    " WHERE schemaname = current_schema() AND tablename = 'content_versions'"
)
_INSERT_SQL = text(
    "INSERT INTO content_versions (id, content_id, content_type, version_number,"
    " snapshot) VALUES (gen_random_uuid()::text, :content, 'carousel_copy', 1, '{}')"
)


def test_revision_is_the_single_head_on_top_of_the_phase_index() -> None:
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [ALEMBIC_HEAD] == [_REVISION]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _global_index_table() -> AsyncIterator[AsyncEngine]:
    """A content_versions table shaped like prod today: the global unique index."""
    async with isolated_schema([_TABLE]) as engine:
        async with engine.begin() as conn:
            await conn.execute(
                text("DROP INDEX IF EXISTS uq_content_versions_content_version")
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX idx_content_versions_version"
                    " ON content_versions (content_type, version_number)"
                )
            )
        yield engine


async def _index_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(_INDEXES_SQL)
    return {str(row[0]) for row in rows}


@requires_postgres
async def test_apply_swaps_the_global_index_for_the_per_content_one() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    async with _global_index_table() as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        names = await _index_names(engine)
        async with engine.begin() as conn:
            await conn.execute(_INSERT_SQL, {"content": "carousel-a"})
            await conn.execute(_INSERT_SQL, {"content": "carousel-b"})

    assert code == EXIT_OK
    assert content_versions_index.GLOBAL_INDEX not in names
    assert content_versions_index.PER_CONTENT_INDEX in names


@requires_postgres
async def test_second_apply_changes_nothing() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    async with _global_index_table() as engine:
        first = await content_versions_index.apply(engine)
        second = await content_versions_index.apply(engine)
        verified = await content_versions_index.verify(engine)

    assert (first.dropped_global, first.created_per_content) == (True, True)
    assert (second.dropped_global, second.created_per_content) == (False, False)
    assert content_versions_index.is_fixed(verified)


@requires_postgres
async def test_verify_fails_while_the_global_index_is_present() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    async with _global_index_table() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await content_versions_index.verify(engine)
        names = await _index_names(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.global_present
    assert not report.per_content_present
    assert content_versions_index.GLOBAL_INDEX in names


@requires_postgres
async def test_a_database_without_the_table_is_left_alone() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    async with isolated_schema([]) as engine:
        code = await run_modes(engine, _modes(apply=True, verify=True))
        applied = await content_versions_index.apply(engine)
        names = await _index_names(engine)

    assert code == EXIT_OK
    assert applied == content_versions_index.IndexReport(
        supported=True, table_present=False
    )
    assert names == set()
