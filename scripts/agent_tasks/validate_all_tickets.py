#!/usr/bin/env python3
"""Validate all tickets; exit 1 on blocking errors."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.constants import TASKS_DIR
from scripts.agent_tasks.schema import load_tickets, validate_ticket_file


def main() -> int:
    tickets = load_tickets(TASKS_DIR)
    blocking = 0
    for ticket in tickets:
        errors = validate_ticket_file(ticket)
        for err in errors:
            print(f"{ticket.ticket_id}: {err}")
            blocking += 1

    if blocking:
        print(f"\n{blocking} validation error(s)")
        return 1

    print(f"All {len(tickets)} ticket(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
