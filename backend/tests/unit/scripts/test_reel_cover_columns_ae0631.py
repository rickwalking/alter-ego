"""The reel cover columns one-shot outside Postgres, and its CLI.

Gherkin: tests/features/reel_cover_columns_oneshot_ae0631.feature
"""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy import String, Uuid
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import reel_cover_columns as columns
from rag_backend.modules.autopilot.infrastructure.cover_models import (
    AutopilotCoverAssetModel,
)
from rag_backend.scripts import reel_cover_columns as cli


# Scenario: The reel cover columns one-shot is a no-op outside Postgres
async def test_sqlite_is_a_no_op_that_says_so() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await columns.apply(engine)
        verified = await columns.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == columns.CoverColumnsReport(supported=False)
    assert verified == columns.CoverColumnsReport(supported=False)
    assert code == cli.EXIT_OK
    assert columns.format_report(applied) == [
        "reel cover columns: not Postgres, nothing to do"
    ]


# Scenario: Verify fails while a reel cover column is missing
def test_report_lines_name_what_was_added_and_what_is_missing() -> None:
    added = columns.CoverColumnsReport(
        supported=True, table_present=True, added=("purpose", "repost_id")
    )
    present = columns.CoverColumnsReport(supported=True, table_present=True)
    missing = columns.CoverColumnsReport(
        supported=True, table_present=True, missing=("repost_id",)
    )
    no_table = columns.CoverColumnsReport(supported=True)
    assert columns.format_report(added) == [
        "reel cover columns: added purpose, repost_id"
    ]
    assert columns.format_report(present) == [
        "reel cover columns: added none (present)"
    ]
    assert columns.format_report(missing) == ["reel cover columns: MISSING repost_id"]
    assert columns.format_report(no_table) == [
        "reel cover columns: no autopilot_cover_assets table yet, nothing to do"
    ]


# Scenario: The reel cover columns one-shot matches the ORM columns
def test_the_one_shot_adds_exactly_the_columns_the_model_maps() -> None:
    table = AutopilotCoverAssetModel.__table__
    assert table.name == columns.COVERS_TABLE
    assert set(columns.COLUMN_DDL) == {"purpose", "repost_id"}
    purpose = table.columns[columns.PURPOSE_COLUMN]
    assert purpose.nullable is False
    assert isinstance(purpose.type, String) and purpose.type.length == 16
    assert purpose.server_default is not None
    assert str(purpose.server_default.arg) == columns.PURPOSE_DEFAULT
    assert "VARCHAR(16) NOT NULL" in columns.COLUMN_DDL[columns.PURPOSE_COLUMN]
    repost = table.columns[columns.REPOST_COLUMN]
    assert repost.nullable is True
    assert isinstance(repost.type, Uuid)


# Scenario: The reel cover columns one-shot matches the ORM columns
def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err
