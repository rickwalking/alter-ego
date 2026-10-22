"""The carousel phase index one-shot outside Postgres, and its CLI.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import carousel_phase_index
from rag_backend.scripts import carousel_phase_index as cli

_NAME = carousel_phase_index.PHASE_INDEX_NAME
_Report = carousel_phase_index.PhaseIndexReport


async def test_sqlite_is_a_no_op_that_says_so() -> None:
    # Scenario: The phase index one-shot is a no-op outside Postgres
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await carousel_phase_index.apply(engine)
        verified = await carousel_phase_index.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
        apply_only = await cli.run_modes(
            engine, argparse.Namespace(apply=True, verify=False)
        )
    finally:
        await engine.dispose()

    assert applied == _Report(supported=False)
    assert verified == _Report(supported=False)
    assert code == cli.EXIT_OK
    assert apply_only == cli.EXIT_OK
    assert carousel_phase_index.format_report(applied) == [
        "carousel phase index: not Postgres, nothing to do"
    ]


def test_report_lines_name_what_happened() -> None:
    # Scenario: The phase index one-shot creates the index once
    lines = carousel_phase_index.format_report
    assert lines(_Report(supported=True, created=True, present=True)) == [
        f"carousel phase index: created {_NAME}"
    ]
    assert lines(
        _Report(supported=True, created=True, rebuilt_invalid=True, present=True)
    ) == [f"carousel phase index: rebuilt invalid {_NAME}"]
    assert lines(_Report(supported=True, present=True)) == [
        f"carousel phase index: {_NAME} present and valid"
    ]
    assert lines(_Report(supported=True)) == [f"carousel phase index: {_NAME} MISSING"]


def test_no_mode_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    # Scenario: The phase index command needs a mode
    assert cli.main([]) == cli.EXIT_USAGE
    assert "--apply and/or --verify" in capsys.readouterr().err


def test_main_runs_against_the_configured_database(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Scenario: The phase index one-shot is a no-op outside Postgres
    class _Settings:
        database_url = "sqlite+aiosqlite:///:memory:"

    monkeypatch.setattr(cli, "get_settings", lambda: _Settings())
    assert cli.main(["--apply", "--verify"]) == cli.EXIT_OK
    assert "nothing to do" in capsys.readouterr().out
