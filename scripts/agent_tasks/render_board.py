#!/usr/bin/env python3
"""Regenerate BOARD.md from ticket Status fields."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.constants import BOARD_COLUMNS, BOARD_PATH, TASKS_DIR
from scripts.agent_tasks.schema import load_tickets


def main() -> int:
    tickets = load_tickets(TASKS_DIR)
    by_status: dict[str, list[str]] = defaultdict(list)
    for ticket in tickets:
        by_status[ticket.status].append(ticket.ticket_id)

    lines = [
        "# Agentic Delivery Board",
        "",
        "Generated view of `.agent/tasks/` (the canonical state) — NOT committed "
        "(gitignored). Regenerate locally with `make board` (or `render_board.py`).",
        "",
    ]
    for column in BOARD_COLUMNS:
        lines.append(f"## {column}")
        lines.append("")
        ids = sorted(by_status.get(column, []))
        if ids:
            lines.extend(f"- {tid}" for tid in ids)
        else:
            lines.append("- None")
        lines.append("")

    BOARD_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {BOARD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
