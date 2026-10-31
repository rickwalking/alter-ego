"""The Instagram insight columns one-shot outside Postgres, and its CLI."""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import ig_insight_columns
from rag_backend.modules.autopilot.infrastructure.insights_models import (
    InstagramPostInsightsModel,
)
from rag_backend.scripts import ig_insight_columns as cli


async def test_sqlite_is_a_no_op_that_says_so() -> None:
    """Scenario: The insight columns one-shot is a no-op outside Postgres"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await ig_insight_columns.apply(engine)
        verified = await ig_insight_columns.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == ig_insight_columns.InsightColumnsReport(supported=False)
    assert verified == ig_insight_columns.InsightColumnsReport(supported=False)
    assert code == cli.EXIT_OK
    assert ig_insight_columns.format_report(applied) == [
        "ig insight columns: not Postgres, nothing to do"
    ]


def test_report_lines_name_what_was_added_and_what_is_missing() -> None:
    """Scenario: Verify fails while an insight column is missing"""
    added = ig_insight_columns.InsightColumnsReport(
        supported=True, table_present=True, added=("likes", "comments")
    )
    missing = ig_insight_columns.InsightColumnsReport(
        supported=True, table_present=True, missing=("avg_watch_time_ms",)
    )
    no_table = ig_insight_columns.InsightColumnsReport(supported=True)
    assert ig_insight_columns.format_report(added) == [
        "ig insight columns: added likes, comments"
    ]
    assert ig_insight_columns.format_report(missing) == [
        "ig insight columns: added none (present)",
        "ig insight columns: MISSING avg_watch_time_ms",
    ]
    assert ig_insight_columns.format_report(no_table) == [
        "ig insight columns: no instagram_post_insights table yet, nothing to do"
    ]


def test_the_one_shot_adds_exactly_nullable_integer_columns_the_model_maps() -> None:
    """Scenario: The one-shot adds exactly the columns the ORM maps"""
    table = InstagramPostInsightsModel.__table__
    assert table.name == ig_insight_columns.INSIGHTS_TABLE
    for name in ig_insight_columns.INSIGHT_COLUMNS:
        column = table.columns[name]
        assert column.nullable is True
        assert isinstance(column.type, Integer)


def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scenario: The insight columns command needs a mode"""
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err
