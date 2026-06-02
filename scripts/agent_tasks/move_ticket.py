#!/usr/bin/env python3
"""Move ticket to a new status with guard checks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.constants import ALL_STATUSES, BOARD_COLUMNS, BOARD_PATH, TASKS_DIR
from scripts.agent_tasks.schema import can_transition, parse_ticket


def find_ticket_path(ticket_id: str) -> Path | None:
    matches = list(TASKS_DIR.glob(f"{ticket_id}*.md"))
    if not matches:
        return None
    return matches[0]


def update_board(board_path: Path, ticket_id: str, new_status: str) -> None:
    content = board_path.read_text(encoding="utf-8")
    line = f"- {ticket_id}"
    content = re.sub(rf"^- {re.escape(ticket_id)}\s*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n{3,}", "\n\n", content)
    marker = f"## {new_status}\n\n"
    if marker not in content:
        raise ValueError(f"Unknown column: {new_status}")
    none_block = f"## {new_status}\n\n- None\n"
    if none_block in content:
        content = content.replace(none_block, f"{marker}- {ticket_id}\n", 1)
    else:
        content = content.replace(marker, f"{marker}- {ticket_id}\n", 1)
    for col in BOARD_COLUMNS:
        section = f"## {col}\n\n"
        if section in content:
            lines = content.split(section, 1)
            if len(lines) > 1:
                rest = lines[1]
                next_idx = rest.find("\n## ")
                body = rest[:next_idx] if next_idx != -1 else rest
                if body.strip() == "":
                    content = content.replace(section, f"{section}- None\n", 1)
    board_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Move ticket status")
    parser.add_argument("ticket_id", help="e.g. AE-0001")
    parser.add_argument("--status", required=True, choices=list(ALL_STATUSES))
    parser.add_argument("--force", action="store_true", help="Skip transition guards")
    args = parser.parse_args()

    path = find_ticket_path(args.ticket_id)
    if path is None:
        print(f"Ticket not found: {args.ticket_id}")
        return 1

    ticket = parse_ticket(path)
    if ticket is None:
        print(f"Could not parse: {path}")
        return 1

    errors = can_transition(ticket, args.status)
    if errors and not args.force:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    content = path.read_text(encoding="utf-8")
    content = re.sub(
        r"^Status:.*$",
        f"Status: {args.status}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(content, encoding="utf-8")
    update_board(BOARD_PATH, args.ticket_id, args.status)
    print(f"{args.ticket_id} → {args.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
