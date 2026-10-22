"""The carousel phase index one-shot on Postgres.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import carousel_phase_index
from rag_backend.scripts.carousel_phase_index import (
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    run_modes,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.integration.test_autopilot_migration import ALEMBIC_HEAD, _alembic_config

_REVISION = "f7a8b9c0d1e2"
_PARENT = "e6f7a8b9c0d1"
_NAME = carousel_phase_index.PHASE_INDEX_NAME
_INDEXES_SQL = text(
    "SELECT c.relname, i.indisvalid FROM pg_index i"
    " JOIN pg_class c ON c.oid = i.indexrelid"
    " JOIN pg_namespace n ON n.oid = c.relnamespace"
    " WHERE c.relname = :name AND n.nspname = current_schema()"
)


_PROJECTS_SQL = text(
    "CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY,"
    " current_phase VARCHAR(50), phase_status VARCHAR(50))"
)


def test_revision_sits_on_top_of_the_palette_change_below_the_single_head() -> None:
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [ALEMBIC_HEAD]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def _modes(*, apply: bool, verify: bool) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, verify=verify)


@asynccontextmanager
async def _projects_without_index() -> AsyncIterator[AsyncEngine]:
    """A carousel_projects table shaped like prod today: no phase index."""
    async with isolated_schema([]) as engine:
        async with engine.begin() as conn:
            await conn.execute(_PROJECTS_SQL)
        yield engine


async def _indexes(engine: AsyncEngine) -> list[tuple[str, bool]]:
    async with engine.connect() as conn:
        rows = await conn.execute(_INDEXES_SQL, {"name": _NAME})
    return [(str(name), bool(valid)) for name, valid in rows]


@requires_postgres
async def test_two_runs_create_the_index_once() -> None:
    """Scenario: The phase index one-shot creates the index once."""
    async with _projects_without_index() as engine:
        assert await _indexes(engine) == []
        first_code = await run_modes(engine, _modes(apply=True, verify=True))
        second = await carousel_phase_index.apply(engine)
        second_code = await run_modes(engine, _modes(apply=True, verify=True))
        indexes = await _indexes(engine)

    assert first_code == EXIT_OK
    assert second_code == EXIT_OK
    assert second.created is False
    assert second.present is True
    assert indexes == [(_NAME, True)]


@requires_postgres
async def test_verify_only_fails_while_the_index_is_missing() -> None:
    """Scenario: Verify fails while the phase index is missing."""
    async with _projects_without_index() as engine:
        code = await run_modes(engine, _modes(apply=False, verify=True))
        report = await carousel_phase_index.verify(engine)

    assert code == EXIT_VERIFY_FAILED
    assert report.present is False
