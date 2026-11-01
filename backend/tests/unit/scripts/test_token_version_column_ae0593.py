"""The ``users.token_version`` one-shot outside Postgres, and its CLI.

Scenarios: ``tests/features/logout_other_sessions_ae0593.feature``.
"""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import token_version_column as column
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.scripts import token_version_column as cli


# Scenario: The token version one-shot leaves other databases alone
async def test_sqlite_is_a_no_op_that_says_so() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await column.apply(engine)
        verified = await column.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == column.VersionColumnReport(supported=False)
    assert verified == column.VersionColumnReport(supported=False)
    assert code == cli.EXIT_OK
    assert column.format_report(applied) == [
        "users token_version: not Postgres, nothing to do"
    ]


# Scenario: Verify fails while token_version is missing
def test_report_lines_name_what_was_added_and_what_is_missing() -> None:
    added = column.VersionColumnReport(supported=True, table_present=True, added=True)
    present = column.VersionColumnReport(supported=True, table_present=True)
    missing = column.VersionColumnReport(
        supported=True, table_present=True, missing=True
    )
    no_table = column.VersionColumnReport(supported=True)

    assert column.format_report(added) == ["users token_version: added"]
    assert column.format_report(present) == ["users token_version: present"]
    assert column.format_report(missing) == [
        "users token_version: MISSING token_version"
    ]
    assert column.format_report(no_table) == [
        "users token_version: no users table yet, nothing to do"
    ]


# Scenario: The token version one-shot matches the ORM column
def test_the_one_shot_adds_the_column_the_model_maps() -> None:
    table = UserModel.__table__
    assert table.name == column.USERS_TABLE
    mapped = table.columns[column.VERSION_COLUMN]
    assert mapped.nullable is False
    assert isinstance(mapped.type, Integer)
    assert mapped.server_default is not None
    assert str(mapped.server_default.arg) == "0"


# Scenario: The token version one-shot matches the ORM column
def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err
