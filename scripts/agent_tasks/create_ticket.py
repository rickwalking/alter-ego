#!/usr/bin/env python3
"""Create a new AE ticket from template.

ID allocation (AE-0238): `next_ticket_id` takes the max AE-#### across local
ticket files AND all git refs, so allocating off an older base cannot reuse an id
already minted on another (unmerged) branch.

Residual parallel-PR window: two PRs opened concurrently can each mint the *same*
new id — neither ref contains the other yet, so both pass their own merge-ref CI.
The collision surfaces on the push-to-`main` run (post-merge), where the now-
blocking duplicate-id check in `validate_all_tickets.py` fails the build. Full
pre-merge prevention would need centralized id reservation (out of scope).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.agent_tasks.board_io import ensure_board, write_board
from scripts.agent_tasks.constants import (
    BOARD_PATH,
    TASKS_DIR,
    TEMPLATE_FULL,
    TEMPLATE_HOTFIX,
    TIER_T1,
)


_ID_RE = re.compile(r"AE-(\d{4})")


def _git_max_ticket_num(tasks_dir: Path) -> int:
    """Highest AE-#### number across ALL git refs (AE-0238).

    `git rev-list --all --objects` enumerates every object reachable from every
    ref — including unmerged local/remote branches — so an id minted on another
    branch is visible even when allocating off an older base. Degrades gracefully
    to 0 (local-only) when git is unavailable or `tasks_dir` is not in a repo.
    """
    git = shutil.which("git")
    if git is None:
        return 0
    try:
        result = subprocess.run(
            [git, "-C", str(tasks_dir), "rev-list", "--all", "--objects"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return 0
    nums = [int(m) for m in _ID_RE.findall(result.stdout)]
    return max(nums, default=0)


def next_ticket_id(tasks_dir: Path) -> str:
    local_max = 0
    for path in tasks_dir.glob("AE-*.md"):
        match = _ID_RE.match(path.name)
        if match:
            local_max = max(local_max, int(match.group(1)))
    global_max = max(local_max, _git_max_ticket_num(tasks_dir))
    return f"AE-{global_max + 1:04d}"


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


def add_to_board(board_path: Path, ticket_id: str, column: str = "Intake") -> None:
    # AE-0237: the board is a gitignored, regenerable view — materialize it from
    # the ticket files first so a fresh clone / CI checkout never crashes here.
    ensure_board(board_path, TASKS_DIR)
    content = board_path.read_text(encoding="utf-8")
    marker = f"## {column}\n\n"
    if marker not in content:
        raise ValueError(f"Column not found: {column}")
    insert = f"- {ticket_id}\n"
    if insert in content:
        return
    content = content.replace(
        marker,
        f"{marker}{insert}",
        1,
    )
    none_line = f"## {column}\n\n- None\n"
    if none_line in content:
        content = content.replace(none_line, marker + insert, 1)
    write_board(board_path, content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create agent ticket")
    parser.add_argument("--title", required=True)
    parser.add_argument("--type", default="Feature")
    parser.add_argument("--area", default="Cross-cutting")
    parser.add_argument("--tier", default="T2", choices=["T1", "T2", "T3"])
    parser.add_argument("--priority", default="Medium")
    args = parser.parse_args()

    ticket_id = next_ticket_id(TASKS_DIR)
    template_name = TEMPLATE_HOTFIX if args.tier == TIER_T1 else TEMPLATE_FULL
    template = (TASKS_DIR / template_name).read_text(encoding="utf-8")
    today = date.today().isoformat()
    slug = slugify(args.title)
    body = template.replace("AE-0000", ticket_id).replace("Ticket Title", args.title)
    body = body.replace("Hotfix Title", args.title)
    body = re.sub(r"^Status:.*$", "Status: Intake", body, count=1, flags=re.MULTILINE)
    body = re.sub(r"^Tier:.*$", f"Tier: {args.tier}", body, count=1, flags=re.MULTILINE)
    body = re.sub(r"^Type:.*$", f"Type: {args.type}", body, count=1, flags=re.MULTILINE)
    body = re.sub(r"^Area:.*$", f"Area: {args.area}", body, count=1, flags=re.MULTILINE)
    body = re.sub(r"^Priority:.*$", f"Priority: {args.priority}", body, count=1, flags=re.MULTILINE)
    body = body.replace("YYYY-MM-DD", today)

    out_path = TASKS_DIR / f"{ticket_id}-{slug}.md"
    out_path.write_text(body, encoding="utf-8")
    add_to_board(BOARD_PATH, ticket_id)
    print(f"Created {out_path}")
    print(f"Ticket ID: {ticket_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
