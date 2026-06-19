#!/usr/bin/env python3
"""Shared board I/O: atomic writes + on-demand regeneration of BOARD.md.

`.agent/BOARD.md` is a gitignored, regenerable view of the canonical
`.agent/tasks/` (AE-0223). Two failure classes are addressed here:

* **AE-0237 (absent board)** — the board-mutating tooling (`create_ticket`,
  `move_ticket`) must never crash with ``FileNotFoundError`` when the board is
  absent (fresh clone / CI / post-merge checkout). The writers call
  :func:`ensure_board` first to materialize it from the ticket files, then apply
  their mutation.
* **Concurrent-writer TOCTOU (cold-critic BLOCKER)** — every write goes through
  :func:`write_board`, which writes a temp file in the same directory and then
  ``os.replace``s it into place. A lost race is recoverable via ``make board``,
  and the atomic swap closes the silent partial-write / drop window.

The board generation logic lives here (not in ``render_board``) so all three
writers share one definition and ``render_board`` stays a thin CLI wrapper.
"""

from __future__ import annotations

import os
import tempfile
from collections import defaultdict
from pathlib import Path

from scripts.agent_tasks.constants import BOARD_COLUMNS
from scripts.agent_tasks.schema import load_tickets

_BOARD_HEADER = (
    "# Agentic Delivery Board",
    "",
    "Generated view of `.agent/tasks/` (the canonical state) — NOT committed "
    "(gitignored). Regenerate locally with `make board` (or `render_board.py`).",
    "",
)


def render_board_text(tasks_dir: Path) -> str:
    """Build the board markdown from the ticket ``Status`` fields (no writes)."""
    by_status: dict[str, list[str]] = defaultdict(list)
    for ticket in load_tickets(tasks_dir):
        by_status[ticket.status].append(ticket.ticket_id)

    lines = list(_BOARD_HEADER)
    for column in BOARD_COLUMNS:
        lines.append(f"## {column}")
        lines.append("")
        ids = sorted(by_status.get(column, []))
        if ids:
            lines.extend(f"- {tid}" for tid in ids)
        else:
            lines.append("- None")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_board(path: Path, text: str) -> None:
    """Atomically write ``text`` to ``path`` (temp file + ``os.replace``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".board-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def ensure_board(board_path: Path, tasks_dir: Path) -> None:
    """Materialize the board from the ticket files when it is absent (AE-0237)."""
    if board_path.exists():
        return
    write_board(board_path, render_board_text(tasks_dir))
