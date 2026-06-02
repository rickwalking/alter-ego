#!/usr/bin/env python3
"""Print handoff summary for a ticket."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.agent_tasks.constants import (
    REPO_ROOT,
    REPORTS_DIR,
    REPORT_DEV_SUFFIX,
    REPORT_QA_SUFFIX,
    TASKS_DIR,
)
from scripts.agent_tasks.schema import parse_ticket


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize ticket for handoff")
    parser.add_argument("ticket_id")
    args = parser.parse_args()

    matches = list(TASKS_DIR.glob(f"{args.ticket_id}*.md"))
    if not matches:
        print(f"Not found: {args.ticket_id}")
        return 1

    ticket = parse_ticket(matches[0])
    if ticket is None:
        return 1

    dev = REPORTS_DIR / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}"
    qa = REPORTS_DIR / f"{ticket.ticket_id}{REPORT_QA_SUFFIX}"

    print(f"## Handoff — {ticket.ticket_id}")
    print(f"- Status: {ticket.status}")
    print(f"- Tier: {ticket.tier}")
    print(f"- Ticket: {ticket.path.relative_to(REPO_ROOT)}")
    print(f"- Dev summary: {dev.relative_to(REPO_ROOT) if dev.exists() else 'missing'}")
    print(f"- QA report: {qa.relative_to(REPO_ROOT) if qa.exists() else 'missing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
