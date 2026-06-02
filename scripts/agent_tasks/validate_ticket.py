#!/usr/bin/env python3
"""Validate a single ticket."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.constants import TASKS_DIR
from scripts.agent_tasks.schema import parse_ticket, validate_ticket_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one ticket")
    parser.add_argument("ticket_id", help="e.g. AE-0001")
    args = parser.parse_args()

    matches = list(TASKS_DIR.glob(f"{args.ticket_id}*.md"))
    if not matches:
        print(f"Not found: {args.ticket_id}")
        return 1

    ticket = parse_ticket(matches[0])
    if ticket is None:
        print("Parse failed")
        return 1

    errors = validate_ticket_file(ticket)
    if errors:
        for err in errors:
            print(f"{ticket.ticket_id}: {err}")
        return 1

    print(f"{ticket.ticket_id}: OK ({ticket.status}, {ticket.tier})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
