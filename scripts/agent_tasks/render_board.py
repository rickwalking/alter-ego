#!/usr/bin/env python3
"""Regenerate BOARD.md from ticket Status fields."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.board_io import render_board_text, write_board
from scripts.agent_tasks.constants import BOARD_PATH, TASKS_DIR


def main() -> int:
    write_board(BOARD_PATH, render_board_text(TASKS_DIR))
    print(f"Wrote {BOARD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
