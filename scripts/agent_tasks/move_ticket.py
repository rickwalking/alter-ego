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
from scripts.agent_tasks.board_io import ensure_board, write_board
from scripts.agent_tasks.constants import (
    ALL_STATUSES,
    BOARD_COLUMNS,
    BOARD_PATH,
    REPORT_DEV_SUFFIX,
    REPORTS_DIR,
    STATUS_DEV_COMPLETE,
    TASKS_DIR,
)
from scripts.agent_tasks.schema import Ticket, can_transition, parse_ticket

# Scaffold for the dev-summary the validator (schema.py) requires at Dev Complete
# / Review. Created on the Dev Complete transition (AE-0169) so the requirement
# can't be silently missed. This does NOT loosen the validator — it only makes
# compliance the default; the developer still fills it in.
DEV_SUMMARY_TEMPLATE = """## Developer Completion Report
Ticket: __TICKET_ID__
Status: Dev Complete

> SCAFFOLD (auto-created by move_ticket.py on the Dev Complete transition, AE-0169).
> Fill this in before moving the ticket to Review — replace every placeholder.

### Summary
<one paragraph: what was implemented>

### Acceptance Criteria Implemented
- [ ] <criterion> — <evidence>

### Files Changed
- <path> — <what changed>

### Tests Run / Gate Reproduction
```
<paste the GATES_JSON summary line; every gate PASS or a justified SKIP>
```

### Integrity (scripts/ci/check-integrity.sh)
Net-new blockers: 0.

### Deviations
None.

### QA Outcome
Pending — run /qa-agent.
"""


def find_ticket_path(ticket_id: str) -> Path | None:
    matches = list(TASKS_DIR.glob(f"{ticket_id}*.md"))
    if not matches:
        return None
    return matches[0]


def scaffold_dev_summary(ticket: Ticket) -> Path | None:
    """Create .agent/reports/<id>.dev-summary.md from a template if it is absent.

    Never overwrites an existing report. Returns the path when created, else None.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORTS_DIR / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}"
    if report.exists():
        return None
    body = DEV_SUMMARY_TEMPLATE.replace("__TICKET_ID__", ticket.ticket_id)
    report.write_text(body, encoding="utf-8")
    return report


def update_board(board_path: Path, ticket_id: str, new_status: str) -> None:
    # AE-0237: regenerate the gitignored board from the ticket files when absent
    # so moving a ticket never crashes on a fresh clone / CI / post-merge tree.
    ensure_board(board_path, TASKS_DIR)
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
    write_board(board_path, content)


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

    if args.status == STATUS_DEV_COMPLETE:
        created = scaffold_dev_summary(ticket)
        if created is not None:
            rel = created.relative_to(_REPO_ROOT)
            print(f"Scaffolded dev-summary: {rel} — fill it in before Review.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
