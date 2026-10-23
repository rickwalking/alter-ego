"""The checkpoint prune CLI and the shared checkpoint thread id.

Feature: backend/tests/features/checkpoint_prune_ae0525.feature
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.channels import DeltaChannel

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.agents.carousel_workflow_graph import build_carousel_workflow_graph
from rag_backend.domain.carousel_checkpoint_thread import checkpoint_thread_id
from rag_backend.domain.constants.checkpoint_prune import (
    AUTOPILOT_RUNS_TABLE,
    AUTOPILOT_SETTLED_STATES,
)
from rag_backend.infrastructure.database.checkpoint_prune import (
    PruneCandidate,
    PruneRefusedError,
    PruneRequest,
)
from rag_backend.infrastructure.database.checkpoint_prune_sql import TableCounts
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.public import AutopilotRunState
from rag_backend.scripts import checkpoint_prune as cli

_THREAD = "0c9a1f0e-5b7e-4a43-9d0e-3f1f6f0d7a11"
_ENGINE = object()


def _args(**flags: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "apply": False,
        "threads": None,
        "backup": None,
        "write_threads": None,
        "ttl_days": 30,
    }
    values.update(flags)
    return argparse.Namespace(**values)


def _candidate() -> PruneCandidate:
    return PruneCandidate(
        thread_id=_THREAD,
        project_id=_THREAD,
        status="failed",
        phase_status="rejected",
        workflow_status="",
        is_public=False,
        archived=True,
        updated_at=datetime(2026, 9, 1, tzinfo=UTC),
        prunable=TableCounts(checkpoints=7, writes=12, blobs=9),
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--apply"],
        ["--apply", "--threads", "t.txt"],
        ["--apply", "--backup", "b.jsonl"],
        ["--threads", "t.txt"],
        ["--backup", "b.jsonl"],
    ],
)
def test_apply_without_sign_off_or_backup_is_a_usage_error(argv: list[str]) -> None:
    """Scenario: Apply without a sign-off file or a backup file is a usage error"""
    runner = AsyncMock()
    with patch.object(cli, "_run_on_own_engine", runner):
        assert cli.main(argv) == cli.EXIT_USAGE
    runner.assert_not_called()


@pytest.mark.parametrize(
    ("ttl", "threads_exist", "backup_exists", "error"),
    [
        ("0", True, False, "--ttl-days must be at least 1"),
        ("-5", True, False, "--ttl-days must be at least 1"),
        ("30", False, False, "the --threads file does not exist"),
        ("30", True, True, "the --backup file already exists"),
    ],
)
def test_a_bad_ttl_or_file_is_a_usage_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    ttl: str,
    threads_exist: bool,
    backup_exists: bool,
    error: str,
) -> None:
    """Scenario: Apply without a sign-off file or a backup file is a usage error"""
    threads = tmp_path / "threads.txt"
    backup = tmp_path / "b.jsonl"
    if threads_exist:
        threads.write_text(f"{_THREAD}\n")
    if backup_exists:
        backup.write_text("kept\n")
    argv = ["--apply", "--ttl-days", ttl, "--threads", str(threads)]
    runner = AsyncMock()
    with patch.object(cli, "_run_on_own_engine", runner):
        assert cli.main([*argv, "--backup", str(backup)]) == cli.EXIT_USAGE
    runner.assert_not_called()
    assert error in capsys.readouterr().err
    assert not backup_exists or backup.read_text() == "kept\n"


def test_the_carousel_graph_has_no_delta_channel() -> None:
    """Scenario: Keep-latest pruning is refused for history-dependent state"""
    graph = build_carousel_workflow_graph().compile()
    delta = [
        name for name, ch in graph.channels.items() if isinstance(ch, DeltaChannel)
    ]
    assert graph.channels
    assert delta == []


async def test_dry_run_prints_states_and_saves_thread_ids(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: A dry run lists the matched threads and deletes nothing"""
    saved = tmp_path / "threads.txt"
    finder = AsyncMock(return_value=[_candidate()])
    applier = AsyncMock()
    with (
        patch.object(cli, "find_candidates", finder),
        patch.object(cli, "apply_prune", applier),
    ):
        code = await cli.run_modes(_ENGINE, _args(write_threads=saved))
    assert code == cli.EXIT_OK
    applier.assert_not_called()
    header, line = capsys.readouterr().out.splitlines()
    assert header.split("\t")[0] == "thread_id"
    assert line.split("\t") == [
        _THREAD,
        "failed",
        "rejected",
        "",
        "false",
        "true",
        "2026-09-01T00:00:00+00:00",
        "7",
        "12",
        "9",
    ]
    assert saved.read_text() == f"{_THREAD}\n"


async def test_apply_prunes_the_signed_off_threads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: The prune deletes only the signed-off threads and keeps a backup"""
    threads = tmp_path / "threads.txt"
    threads.write_text(f"{_THREAD}\n\n  {_THREAD}  \nother\n")
    backup = tmp_path / "backup.jsonl"
    applier = AsyncMock(return_value=TableCounts(checkpoints=3, writes=4, blobs=5))
    with patch.object(cli, "apply_prune", applier):
        code = await cli.run_modes(
            _ENGINE, _args(apply=True, threads=threads, backup=backup)
        )
    assert code == cli.EXIT_OK
    request: PruneRequest = applier.await_args.args[1]
    assert request.thread_ids == (_THREAD, "other")
    assert request.backup_path == backup
    assert "checkpoints=3 writes=4 blobs=5" in capsys.readouterr().out


async def test_a_refused_prune_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: A signed-off thread that is no longer eligible stops the prune"""
    threads = tmp_path / "threads.txt"
    threads.write_text(f"{_THREAD}\n")
    applier = AsyncMock(side_effect=PruneRefusedError("no longer eligible"))
    with patch.object(cli, "apply_prune", applier):
        code = await cli.run_modes(
            _ENGINE,
            _args(apply=True, threads=threads, backup=tmp_path / "b.jsonl"),
        )
    assert code == cli.EXIT_REFUSED
    assert "REFUSED: no longer eligible" in capsys.readouterr().err


def test_engine_and_prune_agree_on_the_thread_id() -> None:
    """Scenario: The workflow engine and the prune agree on the thread id"""
    engine = CarouselWorkflowEngine(checkpointer=None)
    configurable = engine._run_config(_THREAD)["configurable"]
    assert isinstance(configurable, dict)
    assert configurable["thread_id"] == checkpoint_thread_id(_THREAD) == _THREAD


def test_only_finished_autopilot_states_count_as_settled() -> None:
    """Scenario: A carousel whose autopilot run is queued, running or held is never matched"""
    assert AutopilotRunModel.__tablename__ == AUTOPILOT_RUNS_TABLE
    assert set(AUTOPILOT_SETTLED_STATES) == {
        AutopilotRunState.PUBLISHED.value,
        AutopilotRunState.REJECTED.value,
        AutopilotRunState.EXPIRED.value,
    }
