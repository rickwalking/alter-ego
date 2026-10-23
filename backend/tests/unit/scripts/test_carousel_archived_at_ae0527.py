"""The carousel archived_at one-shot outside Postgres, and its CLI."""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import carousel_archived_at
from rag_backend.scripts import carousel_archived_at as cli


async def test_sqlite_is_a_no_op_that_says_so() -> None:
    """Scenario: The archived_at one-shot is a no-op outside Postgres"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await carousel_archived_at.apply(engine)
        verified = await carousel_archived_at.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == carousel_archived_at.ArchivedAtReport(supported=False)
    assert verified == carousel_archived_at.ArchivedAtReport(supported=False)
    assert code == cli.EXIT_OK
    assert carousel_archived_at.format_report(applied) == [
        "carousel archived_at: not Postgres, nothing to do"
    ]


async def test_apply_only_never_fails_the_exit_code() -> None:
    """Scenario: The archived_at one-shot is a no-op outside Postgres"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=False))
    finally:
        await engine.dispose()
    assert code == cli.EXIT_OK


def test_report_lines_name_what_was_added_and_what_is_missing() -> None:
    """Scenario: Verify fails while the column is missing"""
    added = carousel_archived_at.ArchivedAtReport(
        supported=True, column_added=True, index_added=True
    )
    missing = carousel_archived_at.ArchivedAtReport(
        supported=True, missing=(carousel_archived_at.ARCHIVED_AT_INDEX,)
    )
    assert carousel_archived_at.format_report(added) == [
        "carousel archived_at: added archived_at, idx_carousel_projects_archived_at"
    ]
    assert carousel_archived_at.format_report(missing) == [
        "carousel archived_at: added none (present)",
        "carousel archived_at: MISSING idx_carousel_projects_archived_at",
    ]


def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scenario: The archived_at command needs a mode"""
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err
