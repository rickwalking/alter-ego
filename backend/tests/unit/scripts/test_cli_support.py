"""Shared entry point of the guarded maintenance scripts.

Scenario: an invalid mode exits with EXIT_USAGE and reports on stderr.
Scenario: a valid mode runs the async script and returns its exit code.
"""

from __future__ import annotations

import argparse

import pytest

from rag_backend.scripts.cli_support import EXIT_USAGE, GuardedCli, run_guarded_cli


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    return 7 if args.apply else 0


def _validate(args: argparse.Namespace) -> str | None:
    return None if args.apply else "choose --apply"


# Scenario: an invalid mode exits with EXIT_USAGE and reports on stderr.
def test_invalid_mode_returns_usage_and_prints_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = run_guarded_cli(GuardedCli(_parser(), _validate, _run), [])

    assert code == EXIT_USAGE
    assert "ERROR: choose --apply" in capsys.readouterr().err


# Scenario: a valid mode runs the async script and returns its exit code.
def test_valid_mode_returns_the_script_exit_code() -> None:
    assert run_guarded_cli(GuardedCli(_parser(), _validate, _run), ["--apply"]) == 7
