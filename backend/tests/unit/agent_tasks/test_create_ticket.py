"""Tests for create_ticket allocation + board mutation (AE-0237, AE-0238).

The board is a gitignored, regenerable view of `.agent/tasks/` (AE-0223). These
tests pin the AE-0237 contract: `add_to_board` must regenerate the board when it
is absent (never raise FileNotFoundError) and write atomically. They monkeypatch
BOARD_PATH/TASKS_DIR to `tmp_path` so they never touch the real `.agent/` tree.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0238 — test drives git in a throwaway repo (mirrors test_diff_base.py)
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
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0238 — fixed git path, test-controlled args, throwaway repo
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
    # Not a git repo => git-ref scan degrades to local-only (here: empty => AE-0001).
    assert create_ticket.next_ticket_id(tmp_path) == "AE-0001"


# AE-0238 Gherkin: an id that exists only on an unmerged branch must not be reused.
def test_next_ticket_id_sees_ids_on_other_branches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    tasks_dir = repo / ".agent" / "tasks"
    tasks_dir.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    # Base carries AE-0001 so .agent/tasks exists on every branch (as in the real
    # repo); the working tree alone would only ever allocate AE-0002.
    _seed_ticket(tasks_dir, "AE-0001")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base ticket")
    base_branch = _git(repo, "branch", "--show-current").strip()  # main or master

    # AE-0600 lives only on a feature branch, never on the base checkout.
    _git(repo, "checkout", "-q", "-b", "feature")
    _seed_ticket(tasks_dir, "AE-0600")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add AE-0600")
    _git(repo, "checkout", "-q", base_branch)  # base lacks AE-0600 in the tree

    assert not (tasks_dir / "AE-0600-example.md").exists()  # absent locally
    # Working-tree-only allocation would return AE-0002; the git-ref scan sees
    # AE-0600 on the feature ref → next is AE-0601.
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


# Seeded-regression proof (AE-0237): the absent-board path must NOT raise
# FileNotFoundError — it reproduces the FC-1 crash on the pre-fix code.
def test_add_to_board_regenerates_when_board_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _seed_ticket(tasks_dir, "AE-0042")
    board = tmp_path / "BOARD.md"
    assert not board.exists()
    monkeypatch.setattr(create_ticket, "TASKS_DIR", tasks_dir)

    create_ticket.add_to_board(board, "AE-0042")

    content = board.read_text(encoding="utf-8")
    assert "- AE-0042" in content
    # Regenerated from the ticket files => carries the full column scaffold.
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
