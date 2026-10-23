"""The content_versions index one-shot outside Postgres, and its CLI.

Feature: backend/tests/features/carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

import argparse

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.infrastructure.database import content_versions_index
from rag_backend.scripts import content_versions_index as cli


async def test_sqlite_is_a_no_op_that_says_so() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        applied = await content_versions_index.apply(engine)
        verified = await content_versions_index.verify(engine)
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=True))
    finally:
        await engine.dispose()

    assert applied == content_versions_index.IndexReport(supported=False)
    assert verified == content_versions_index.IndexReport(supported=False)
    assert code == cli.EXIT_OK
    assert content_versions_index.format_report(applied) == [
        "content_versions index: not Postgres, nothing to do"
    ]


async def test_apply_only_never_fails_the_exit_code() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        code = await cli.run_modes(engine, argparse.Namespace(apply=True, verify=False))
    finally:
        await engine.dispose()
    assert code == cli.EXIT_OK


def test_report_and_fixed_state() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    fixed = content_versions_index.IndexReport(supported=True, per_content_present=True)
    broken = content_versions_index.IndexReport(
        supported=True, global_present=True, per_content_present=True
    )
    assert content_versions_index.is_fixed(fixed)
    assert not content_versions_index.is_fixed(broken)
    assert not content_versions_index.is_fixed(
        content_versions_index.IndexReport(supported=True)
    )
    assert content_versions_index.format_report(broken) == [
        "content_versions index: dropped global False, created per-content False,"
        " global present True, per-content present True"
    ]


def test_cli_without_a_mode_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    assert cli.main([]) == cli.EXIT_USAGE
    assert "choose --apply and/or --verify" in capsys.readouterr().err


def test_a_missing_table_reads_as_fixed() -> None:
    """Scenario: The deploy fixes the content versions unique index once."""
    report = content_versions_index.IndexReport(supported=True, table_present=False)
    assert content_versions_index.is_fixed(report)
    assert content_versions_index.format_report(report) == [
        "content_versions index: no content_versions table, nothing to do"
    ]
