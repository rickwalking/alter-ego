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


def _blocking_duplicate_ids(tickets: list[Ticket]) -> int:
    """Fail (blocking) on ticket IDs claimed by more than one file (AE-0238).

    Two files sharing one AE-#### id is the report-freeload root cause: both
    resolve to the same `<id>.dev-summary.md` / `<id>.qa.md` slot, so one ticket
    can satisfy its report gate on a report authored for the other. AE-0181 added
    the per-report attribution check but left this *non-blocking* ("renumbering
    tracked separately"). Two real collisions since (AE-0145..0148 → AE-0224..0227
    and an AE-0228 near-miss) override that choice: this now BLOCKS (contributes to
    the exit code). The attribution check stays as defense in depth. Returns the
    number of duplicated IDs so the caller can fold it into the blocking count.
    """
    counts = Counter(t.ticket_id for t in tickets)
    dupes = sorted(tid for tid, n in counts.items() if n > 1)
    if not dupes:
        return 0
    print("ERROR: duplicate ticket IDs (report-freeload risk, AE-0238):")
    for tid in dupes:
        files = ", ".join(sorted(t.path.name for t in tickets if t.ticket_id == tid))
        print(f"  {tid} claimed by {counts[tid]} files: {files}")
    print("  -> renumber the colliding file(s) to a unique id. The allocator now")
    print("     scans git refs (create_ticket.next_ticket_id) so a fresh ticket")
    print("     no longer reuses an id minted on another branch.\n")
    return len(dupes)


def main() -> int:
    tickets = load_tickets(TASKS_DIR)
    blocking = _blocking_duplicate_ids(tickets)
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
