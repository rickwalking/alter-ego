#!/usr/bin/env python3
"""Validate all tickets; exit 1 on blocking errors."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.constants import TASKS_DIR
from scripts.agent_tasks.schema import Ticket, load_tickets, validate_ticket_file


def _warn_duplicate_ids(tickets: list[Ticket]) -> None:
    """Surface (non-blocking) ticket IDs claimed by more than one file (AE-0181).

    Two files sharing one AE-#### id is the report-freeload root cause: both
    resolve to the same `<id>.dev-summary.md` / `<id>.qa.md` slot, so one ticket
    can satisfy its report gate on a report authored for the other. The schema's
    per-report attribution check (AE-0181) binds a report to its id, but the
    renumbering itself is tracked separately (AE-0181 non-goal), so this is a
    WARNING for visibility — it does not fail the board.
    """
    counts = Counter(t.ticket_id for t in tickets)
    dupes = sorted(tid for tid, n in counts.items() if n > 1)
    if not dupes:
        return
    print("WARNING: duplicate ticket IDs (report-freeload risk, AE-0181):")
    for tid in dupes:
        files = ", ".join(sorted(t.path.name for t in tickets if t.ticket_id == tid))
        print(f"  {tid} claimed by {counts[tid]} files: {files}")
    print("  -> renumber to a unique id (tracked separately); reports are still")
    print("     attribution-checked per id so cross-ticket freeload is blocked.\n")


def main() -> int:
    tickets = load_tickets(TASKS_DIR)
    _warn_duplicate_ids(tickets)
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
