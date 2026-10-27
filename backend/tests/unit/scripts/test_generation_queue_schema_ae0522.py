"""The queue schema one-shot outside Postgres, its CLI and its DDL."""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.modules.generation_queue.infrastructure import schema
from rag_backend.modules.generation_queue.infrastructure.models import (
    CarouselGenerationEventModel,
    GenerationRunModel,
)
from rag_backend.scripts import generation_queue_schema as cli


async def test_sqlite_is_a_no_op_that_says_so() -> None:
    """Scenario: The queue schema one-shot is a no-op outside Postgres"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await schema.apply(engine)
        verified = await schema.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
        apply_only = await cli.run_modes(
            engine, argparse.Namespace(apply=True, verify=False)
        )
    finally:
        await engine.dispose()
    assert applied == schema.QueueSchemaReport(supported=False)
    assert verified == schema.QueueSchemaReport(supported=False)
    assert code == cli.EXIT_OK
    assert apply_only == cli.EXIT_OK
    assert schema.format_report(applied) == [
        "generation queue schema: not Postgres, nothing to do"
    ]


def test_report_lines() -> None:
    """Scenario: Verify fails while a queue object is missing"""
    applied = schema.QueueSchemaReport(
        supported=True, created=("generation_runs",), pgqueuer="installed"
    )
    missing = schema.QueueSchemaReport(supported=True, missing=("pgqueuer",))
    present = schema.QueueSchemaReport(supported=True)
    assert schema.format_report(applied) == [
        "generation queue schema: created generation_runs",
        "generation queue schema: pgqueuer installed",
    ]
    assert schema.format_report(missing) == [
        "generation queue schema: MISSING pgqueuer"
    ]
    assert schema.format_report(present) == ["generation queue schema: all present"]


async def test_ddl_is_compiled_from_the_orm_table() -> None:
    """Scenario: The queue schema reaches prod with the deploy"""
    engine = create_async_engine("postgresql+asyncpg://user:pw@db.invalid/app")
    statements = schema.generation_runs_ddl(engine.dialect)
    await engine.dispose()
    table = statements[0]
    assert table.startswith("\nCREATE TABLE IF NOT EXISTS generation_runs")
    for column in GenerationRunModel.__table__.columns:
        assert f"\t{column.name} " in table
    assert "JSONB" in table
    indexes = statements[1:]
    assert len(indexes) == 4
    assert all(item.startswith("CREATE ") for item in indexes)
    unique = [item for item in indexes if "UNIQUE" in item]
    assert len(unique) == 1
    assert "WHERE status IN ('queued', 'running', 'retry_wait')" in unique[0]


async def test_generation_event_ddl_is_compiled_from_the_orm() -> None:
    """Scenario: The queue schema reaches prod with the deploy"""
    engine = create_async_engine("postgresql+asyncpg://user:pw@db.invalid/app")
    statements = schema.generation_events_ddl(engine.dialect)
    await engine.dispose()

    table = statements[0]
    assert table.startswith("\nCREATE TABLE IF NOT EXISTS carousel_generation_events")
    for column in CarouselGenerationEventModel.__table__.columns:
        assert f"\t{column.name} " in table
    assert "JSONB" in table
    assert 'ON DELETE CASCADE' in table
    assert len(statements[1:]) == 3
    assert all(item.startswith("CREATE INDEX IF NOT EXISTS") for item in statements[1:])


def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scenario: The queue schema command needs a mode"""
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err


def test_rollback_cli_needs_a_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: A revert of the worker hands the queued work back"""
    from rag_backend.scripts import generation_queue_rollback

    assert generation_queue_rollback.main([]) == generation_queue_rollback.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err
