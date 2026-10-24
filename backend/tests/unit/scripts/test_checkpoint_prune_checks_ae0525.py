"""The safety checks of the checkpoint prune CLI: pg_dump, DeltaChannel, backup files.

Feature: backend/tests/features/checkpoint_prune_ae0525.feature
"""

from __future__ import annotations

import argparse
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, TypedDict
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.channels import DeltaChannel
from langgraph.graph import END, START, StateGraph

from rag_backend.infrastructure.database.checkpoint_prune_backup import (
    PruneRefusedError,
    restore_backup,
    verify_pg_dump,
)
from rag_backend.infrastructure.database.checkpoint_prune_sql import TableCounts
from rag_backend.scripts import checkpoint_prune as cli

_ENGINE = object()
_LISTING = (
    ";\n; Archive created at 2026-10-24\n;\n"
    "3456; 0 16390 TABLE DATA public checkpoints rag_user\n"
    "3457; 0 16398 TABLE DATA public checkpoint_writes rag_user\n"
    "3458; 0 16405 TABLE DATA public checkpoint_blobs rag_user\n"
)


def _fake_pg_restore(folder: Path, listing: str, code: int) -> Path:
    folder.mkdir()
    script = folder / "pg_restore"
    body = "".join(f"echo '{line}'\n" for line in listing.splitlines())
    script.write_text(f"#!/bin/sh\n{body}echo 'bad archive' >&2\nexit {code}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return folder


def _append(state: list[str] | None, writes: list[list[str]]) -> list[str]:
    return [*(state or []), *(item for write in writes for item in write)]


class _DeltaState(TypedDict):
    log: Annotated[list[str], DeltaChannel(_append)]


class _PlainState(TypedDict):
    note: str


def _graph_with_delta_in_a_subgraph() -> StateGraph[_PlainState]:
    child = StateGraph(_DeltaState)
    child.add_node("step", lambda state: {"log": ["x"]})
    child.add_edge(START, "step")
    child.add_edge("step", END)
    parent = StateGraph(_PlainState)
    parent.add_node("child", child.compile())
    parent.add_edge(START, "child")
    parent.add_edge("child", END)
    return parent


def _apply_args(tmp_path: Path) -> argparse.Namespace:
    threads = tmp_path / "threads.txt"
    threads.write_text("t1\n")
    return argparse.Namespace(
        apply=True,
        threads=threads,
        pg_dump=tmp_path / "checkpoints.dump",
        backup=tmp_path / "b.jsonl",
        restore=None,
        write_threads=None,
        ttl_days=30,
    )


async def test_a_readable_dump_of_the_three_tables_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Apply refuses without a readable pg_dump of the checkpoint tables"""
    monkeypatch.setenv("PATH", str(_fake_pg_restore(tmp_path / "bin", _LISTING, 0)))
    await verify_pg_dump(tmp_path / "checkpoints.dump")


async def test_a_dump_without_a_table_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Apply refuses without a readable pg_dump of the checkpoint tables"""
    listing = "\n".join(_LISTING.splitlines()[:-1])
    monkeypatch.setenv("PATH", str(_fake_pg_restore(tmp_path / "bin", listing, 0)))
    with pytest.raises(PruneRefusedError, match="no data for: checkpoint_blobs"):
        await verify_pg_dump(tmp_path / "checkpoints.dump")


async def test_an_unreadable_dump_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Apply refuses without a readable pg_dump of the checkpoint tables"""
    monkeypatch.setenv("PATH", str(_fake_pg_restore(tmp_path / "bin", "", 1)))
    with pytest.raises(PruneRefusedError, match=r"cannot read .*bad archive"):
        await verify_pg_dump(tmp_path / "checkpoints.dump")


async def test_a_missing_pg_restore_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Apply refuses without a readable pg_dump of the checkpoint tables"""
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(PruneRefusedError, match="pg_restore is not installed"):
        await verify_pg_dump(tmp_path / "checkpoints.dump")


async def test_a_refused_dump_deletes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Apply refuses without a readable pg_dump of the checkpoint tables"""
    applier = AsyncMock()
    verifier = AsyncMock(side_effect=PruneRefusedError("no data for: checkpoints"))
    with (
        patch.object(cli, "apply_prune", applier),
        patch.object(cli, "verify_pg_dump", verifier),
    ):
        code = await cli.run_modes(_ENGINE, _apply_args(tmp_path))
    assert code == cli.EXIT_REFUSED
    applier.assert_not_called()
    assert "REFUSED: no data for: checkpoints" in capsys.readouterr().err


def test_delta_channels_are_found_in_subgraphs() -> None:
    """Scenario: Keep-latest pruning is refused for history-dependent state"""
    with patch.object(
        cli, "build_carousel_workflow_graph", _graph_with_delta_in_a_subgraph
    ):
        assert cli.delta_channels() == ["child:log"]


async def test_a_graph_with_a_delta_channel_refuses_the_prune(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Keep-latest pruning is refused for history-dependent state"""
    applier = AsyncMock()
    verifier = AsyncMock()
    with (
        patch.object(
            cli, "build_carousel_workflow_graph", _graph_with_delta_in_a_subgraph
        ),
        patch.object(cli, "apply_prune", applier),
        patch.object(cli, "verify_pg_dump", verifier),
    ):
        code = await cli.run_modes(_ENGINE, _apply_args(tmp_path))
    assert code == cli.EXIT_REFUSED
    applier.assert_not_called()
    verifier.assert_not_called()
    assert "history-dependent state: child:log" in capsys.readouterr().err


async def test_the_default_backup_goes_to_the_mounted_output_volume(
    tmp_path: Path,
) -> None:
    """Scenario: The prune deletes only the signed-off threads and keeps a backup"""
    args = _apply_args(tmp_path)
    args.backup = None
    output = tmp_path / "output"
    settings = SimpleNamespace(
        carousel_output_dir=str(output / "carousels"), carousel_checkpoint_ttl_days=30
    )
    applier = AsyncMock(return_value=TableCounts(checkpoints=1))
    with (
        patch.object(cli, "get_settings", return_value=settings),
        patch.object(cli, "apply_prune", applier),
        patch.object(cli, "verify_pg_dump", AsyncMock()),
    ):
        assert await cli.run_modes(_ENGINE, args) == cli.EXIT_OK
    backup = applier.await_args.args[1].backup_path
    assert backup.parent == output / "checkpoint-prune"
    assert backup.name.startswith("checkpoint-prune-")
    assert backup.suffix == ".jsonl"
    assert not backup.exists()
    assert stat.S_IMODE(backup.parent.stat().st_mode) == 0o700


@pytest.mark.parametrize(
    "extra", [["--apply"], ["--threads", "t.txt"], ["--backup", "b.jsonl"]]
)
def test_restore_goes_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra: list[str]
) -> None:
    """Scenario: A JSONL backup restores every pruned row"""
    backup = tmp_path / "b.jsonl"
    backup.write_text("")
    runner = AsyncMock()
    with patch.object(cli, "_run_on_own_engine", runner):
        assert cli.main(["--restore", str(backup), *extra]) == cli.EXIT_USAGE
        assert cli.main(["--restore", str(tmp_path / "none.jsonl")]) == cli.EXIT_USAGE
    runner.assert_not_called()
    err = capsys.readouterr().err
    assert "--restore goes alone" in err
    assert "the --restore file does not exist" in err


async def test_restore_mode_reports_the_restored_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: A JSONL backup restores every pruned row"""
    args = argparse.Namespace(restore=tmp_path / "b.jsonl", apply=False)
    restorer = AsyncMock(return_value=TableCounts(checkpoints=2, writes=3, blobs=4))
    with patch.object(cli, "restore_backup", restorer):
        assert await cli.run_modes(_ENGINE, args) == cli.EXIT_OK
    restorer.assert_awaited_once_with(_ENGINE, args.restore)
    assert "restored checkpoints=2 writes=3 blobs=4" in capsys.readouterr().out


async def test_a_malformed_backup_line_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: A JSONL backup restores every pruned row"""
    backup = tmp_path / "b.jsonl"
    backup.write_text('{"table": "users", "row": {"id": 1}}\n')
    with pytest.raises(PruneRefusedError, match="line 1 is not a checkpoint"):
        await restore_backup(AsyncMock(), backup)
    args = argparse.Namespace(restore=backup, apply=False)
    assert await cli.run_modes(_ENGINE, args) == cli.EXIT_REFUSED
    assert "REFUSED: backup line 1" in capsys.readouterr().err
