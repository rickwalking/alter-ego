"""The ``users.must_change_password`` one-shot outside Postgres, and its CLI."""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy import Boolean
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import must_change_password_column as column
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.scripts import must_change_password_column as cli


# Scenario: The must_change_password one-shot is a no-op outside Postgres
async def test_sqlite_is_a_no_op_that_says_so() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await column.apply(engine)
        verified = await column.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == column.FlagColumnReport(supported=False)
    assert verified == column.FlagColumnReport(supported=False)
    assert code == cli.EXIT_OK
    assert column.format_report(applied) == [
        "users must_change_password: not Postgres, nothing to do"
    ]


# Scenario: Verify fails while must_change_password is missing
def test_report_lines_name_what_was_added_and_what_is_missing() -> None:
    added = column.FlagColumnReport(supported=True, table_present=True, added=True)
    present = column.FlagColumnReport(supported=True, table_present=True)
    missing = column.FlagColumnReport(supported=True, table_present=True, missing=True)
    no_table = column.FlagColumnReport(supported=True)

    assert column.format_report(added) == ["users must_change_password: added"]
    assert column.format_report(present) == ["users must_change_password: present"]
    assert column.format_report(missing) == [
        "users must_change_password: MISSING must_change_password"
    ]
    assert column.format_report(no_table) == [
        "users must_change_password: no users table yet, nothing to do"
    ]


# Scenario: The column one-shot matches the ORM column
def test_the_one_shot_adds_the_column_the_model_maps() -> None:
    table = UserModel.__table__
    assert table.name == column.USERS_TABLE
    mapped = table.columns[column.FLAG_COLUMN]
    assert mapped.nullable is False
    assert isinstance(mapped.type, Boolean)
    assert mapped.server_default is not None
    assert str(mapped.server_default.arg) == "false"


# Scenario: The must_change_password command needs a mode
def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err
