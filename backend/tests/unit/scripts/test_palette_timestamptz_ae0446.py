"""The palette timestamptz one-shot outside Postgres, and its CLI (AE-0446).

Feature: backend/tests/features/palette_timestamptz_ae0446.feature
"""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import palette_timestamptz
from rag_backend.scripts import palette_timestamptz as cli


# Scenario: The one-shot is a no-op outside Postgres
async def test_sqlite_is_a_no_op_that_says_so() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await palette_timestamptz.apply(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == palette_timestamptz.TimestamptzReport(supported=False)
    assert code == cli.EXIT_OK
    assert palette_timestamptz.format_report(applied) == [
        "palette timestamptz: not Postgres, nothing to do"
    ]


async def test_apply_only_never_fails_the_exit_code() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=False))
    finally:
        await engine.dispose()
    assert code == cli.EXIT_OK


def test_report_lines_name_what_changed() -> None:
    report = palette_timestamptz.TimestamptzReport(
        supported=True, altered=("created_at",)
    )
    assert palette_timestamptz.format_report(report) == [
        "palette timestamptz: altered created_at"
    ]
    untouched = palette_timestamptz.TimestamptzReport(supported=True)
    assert palette_timestamptz.format_report(untouched) == [
        "palette timestamptz: altered none (already timestamptz)"
    ]


# Scenario: The command needs a mode
def test_no_mode_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == cli.EXIT_USAGE
    assert "--apply and/or --verify" in capsys.readouterr().err


def test_main_runs_against_the_configured_database(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class _Settings:
        database_url = "sqlite+aiosqlite:///:memory:"

    monkeypatch.setattr(cli, "get_settings", lambda: _Settings())
    assert cli.main(["--apply", "--verify"]) == cli.EXIT_OK
    assert "nothing to do" in capsys.readouterr().out
