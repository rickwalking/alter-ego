"""Tests for create_ticket allocation + board mutation.

The board is a gitignored, regenerable view of `.agent/tasks/`. These
tests pin the contract: `add_to_board` must regenerate the board when it
is absent (never raise FileNotFoundError) and write atomically. They monkeypatch
BOARD_PATH/TASKS_DIR to `tmp_path` so they never touch the real `.agent/` tree.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: test drives git in a throwaway repo (mirrors test_diff_base.py)
from pathlib import Path

import pytest
from scripts.agent_tasks import board_io, create_ticket
from scripts.agent_tasks.constants import BOARD_COLUMNS

_GIT = shutil.which("git") or "git"


def _seed_ticket(tasks_dir: Path, ticket_id: str, status: str = "Intake") -> None:
    (tasks_dir / f"{ticket_id}-example.md").write_text(
        f"# {ticket_id} — Example\n\nStatus: {status}\nTier: T2\n",
        encoding="utf-8",
    )


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed git path, test-controlled args, throwaway repo
        [_GIT, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_next_ticket_id_returns_max_plus_one(tmp_path: Path) -> None:
    _seed_ticket(tmp_path, "AE-0001")
    _seed_ticket(tmp_path, "AE-0007")
    assert create_ticket.next_ticket_id(tmp_path) == "AE-0008"


def test_next_ticket_id_empty_dir_starts_at_one(tmp_path: Path) -> None:
    """Outside a git repo the git-ref scan degrades to a local-only scan."""
    assert create_ticket.next_ticket_id(tmp_path) == "AE-0001"


def test_next_ticket_id_sees_ids_on_other_branches(tmp_path: Path) -> None:
    """An id that exists only on an unmerged branch must not be reused. The base branch
    carries the first ticket so .agent/tasks exists on every branch (as in the real
    repo); a working-tree-only allocation would return the second id, while the git-ref
    scan sees the feature-branch id and allocates the one after it.
    """
    repo = tmp_path / "repo"
    tasks_dir = repo / ".agent" / "tasks"
    tasks_dir.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _seed_ticket(tasks_dir, "AE-0001")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base ticket")
    base_branch = _git(repo, "branch", "--show-current").strip()

    _git(repo, "checkout", "-q", "-b", "feature")
    _seed_ticket(tasks_dir, "AE-0600")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add AE-0600")
    _git(repo, "checkout", "-q", base_branch)

    assert not (tasks_dir / "AE-0600-example.md").exists()
    assert create_ticket.next_ticket_id(tasks_dir) == "AE-0601"


def test_add_to_board_with_board_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    board = tmp_path / "BOARD.md"
    board.write_text(board_io.render_board_text(tasks_dir), encoding="utf-8")
    monkeypatch.setattr(create_ticket, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(board_io, "load_tickets", lambda _d: [])

    create_ticket.add_to_board(board, "AE-0099")

    assert "- AE-0099" in board.read_text(encoding="utf-8")


def test_add_to_board_regenerates_when_board_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Seeded-regression proof: the absent-board path must NOT raise FileNotFoundError,
    as the pre-fix code did. The regenerated board carries the full column scaffold.
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _seed_ticket(tasks_dir, "AE-0042")
    board = tmp_path / "BOARD.md"
    assert not board.exists()
    monkeypatch.setattr(create_ticket, "TASKS_DIR", tasks_dir)

    create_ticket.add_to_board(board, "AE-0042")

    content = board.read_text(encoding="utf-8")
    assert "- AE-0042" in content
    for column in BOARD_COLUMNS:
        assert f"## {column}" in content


def test_add_to_board_is_atomic_no_temp_left_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    board = tmp_path / "BOARD.md"
    monkeypatch.setattr(create_ticket, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(board_io, "load_tickets", lambda _d: [])

    create_ticket.add_to_board(board, "AE-0100")

    leftovers = list(tmp_path.glob(".board-*.tmp"))
    assert leftovers == []
