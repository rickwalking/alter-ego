"""CLI surface of the hidden-post rebuild script (parser + summary + exit code)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from rag_backend.application.services.blog.blog_rebuild import (
    RebuildEntry,
    RebuildReport,
    RebuildSelection,
)
from rag_backend.scripts import rebuild_hidden_posts as cli


def test_default_is_dry_run() -> None:
    assert cli.build_parser().parse_args([]).apply is False


def test_apply_flag_is_opt_in() -> None:
    assert cli.build_parser().parse_args(["--apply"]).apply is True


def test_dry_run_flag_is_accepted_and_excludes_apply() -> None:
    assert cli.build_parser().parse_args(["--dry-run"]).apply is False
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--apply", "--dry-run"])


def test_only_is_repeatable_and_caps_parse() -> None:
    args = cli.build_parser().parse_args([
        "--only",
        "post-a",
        "--only",
        "post-b",
        "--limit",
        "2",
        "--max-posts",
        "3",
        "--include-published",
    ])
    selection = cli.selection_from_args(args)
    assert selection == RebuildSelection(
        only=frozenset({"post-a", "post-b"}),
        limit=2,
        max_posts=3,
        allow_published=True,
    )


def test_max_posts_defaults_to_one() -> None:
    args = cli.build_parser().parse_args([])
    assert cli.selection_from_args(args).max_posts == cli.DEFAULT_MAX_POSTS
    assert cli.DEFAULT_MAX_POSTS == 1


def test_caps_reject_zero() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--limit", "0"])
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--max-posts", "0"])


def test_format_report_lists_the_summary_and_the_entries() -> None:
    report = RebuildReport(
        selected=[RebuildEntry("post-a", "hidden_bad_post")],
        rebuilt=[RebuildEntry("post-a", "rebuilt", "complete")],
        skipped=[RebuildEntry("post-b", "already_rebuilt")],
        failed=[RebuildEntry("post-c", "failed", "RuntimeError")],
    )
    lines = [line.strip() for line in cli.format_report(report)]
    assert lines[0] == "summary: selected=1 rebuilt=1 skipped=1 failed=1"
    assert "rebuilt post-a (complete)" in lines
    assert "skipped post-b (already_rebuilt)" in lines
    assert "failed  post-c (RuntimeError)" in lines


def test_format_report_reports_omitted_rows() -> None:
    report = RebuildReport(omitted=4)
    assert cli.format_report(report)[0].endswith("omitted=4")


def test_exit_code_is_nonzero_when_a_post_failed() -> None:
    assert cli.exit_code(RebuildReport()) == cli.EXIT_OK
    failed = RebuildReport(failed=[RebuildEntry("post-a", "failed", "boom")])
    assert cli.exit_code(failed) == cli.EXIT_FAILED


class _FakeService:
    def __init__(self, report: RebuildReport) -> None:
        self._report = report
        self.selection: RebuildSelection | None = None

    async def run(self, selection: RebuildSelection) -> RebuildReport:
        self.selection = selection
        return self._report

    async def preview(self, selection: RebuildSelection) -> RebuildReport:
        self.selection = selection
        return self._report


def _patch_run_deps(monkeypatch: pytest.MonkeyPatch, service: object) -> None:
    settings = SimpleNamespace(
        database_url="sqlite+aiosqlite://",
        debug=False,
        langfuse_public_key=None,
        langfuse_secret_key=None,
        langfuse_host="",
    )

    async def _init_db(_url: str) -> None:
        return None

    async def _close_db() -> None:
        return None

    async def _checkpointer(_settings: object, _stack: object) -> None:
        return None

    from rag_backend.agents import harness
    from rag_backend.bootstrap import blog_rebuild as bootstrap_rebuild
    from rag_backend.infrastructure.config import settings as settings_module
    from rag_backend.infrastructure.database import config as db_config

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    monkeypatch.setattr(db_config, "init_db", _init_db)
    monkeypatch.setattr(db_config, "close_db", _close_db)
    monkeypatch.setattr(cli, "_init_langfuse", lambda: None)
    monkeypatch.setattr(cli, "_flush_langfuse", lambda: None)
    monkeypatch.setattr(harness, "build_checkpointer", _checkpointer)
    monkeypatch.setattr(bootstrap_rebuild, "build_rebuild_service", lambda _cp: service)


async def test_run_returns_nonzero_and_prints_the_summary_on_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = RebuildReport(failed=[RebuildEntry("post-a", "failed", "boom")])
    service = _FakeService(report)
    _patch_run_deps(monkeypatch, service)
    selection = RebuildSelection(max_posts=1)
    assert await cli._run(apply=True, selection=selection) == cli.EXIT_FAILED
    assert service.selection == selection
    assert "failed=1" in capsys.readouterr().out


async def test_run_prints_the_summary_when_setup_aborts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _boom(_cp: object) -> object:
        raise RuntimeError("wiring failed")

    from rag_backend.bootstrap import blog_rebuild as bootstrap_rebuild

    _patch_run_deps(monkeypatch, _FakeService(RebuildReport()))
    monkeypatch.setattr(bootstrap_rebuild, "build_rebuild_service", _boom)
    assert await cli._run(apply=False, selection=RebuildSelection()) == cli.EXIT_FAILED
    assert "summary: selected=0" in capsys.readouterr().out


def test_main_returns_the_run_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_run(*, apply: bool, selection: RebuildSelection) -> int:
        captured["apply"] = apply
        captured["selection"] = selection
        return cli.EXIT_FAILED

    from rag_backend.infrastructure import logging as logging_module
    from rag_backend.infrastructure.config import settings as settings_module

    monkeypatch.setattr(cli, "_run", _fake_run)
    monkeypatch.setattr(logging_module, "setup_logging", lambda **_kwargs: None)
    monkeypatch.setattr(
        settings_module, "get_settings", lambda: SimpleNamespace(debug=False)
    )
    assert cli.main(["--apply", "--only", "post-a"]) == cli.EXIT_FAILED
    assert captured["apply"] is True
    assert captured["selection"] == RebuildSelection(
        only=frozenset({"post-a"}), max_posts=cli.DEFAULT_MAX_POSTS
    )
