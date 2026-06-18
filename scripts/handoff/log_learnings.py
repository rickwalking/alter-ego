#!/usr/bin/env python3
"""Append a session's learnings to the durable kaizen signal log.

The `/handoff` skill calls this after writing `HANDOFF-latest.json`. It distils
the handoff's learning-bearing fields (problems + root causes, landmines,
decisions) into one compact record appended to
`.agent/handoff/learnings-log.jsonl` — the append-only signal that the kaizen
`session` mode mines across sessions to propose systemic improvements.

This is deliberately a tiny, deterministic, stdlib-only helper (not model logic)
so the signal is captured the same way every time. Idempotent per handoff:
re-running for the same `created_at` does not double-append.

Usage:
    python3 log_learnings.py [<repo_root>]   # defaults to cwd
Exit code is always 0 unless given an unreadable handoff (1), so a handoff write
is never silently dropped without signal.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__:
    from scripts.handoff import constants as C
else:  # pragma: no cover - exercised only via direct CLI invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.handoff import constants as C

# Fields lifted from the handoff JSON into the learnings record (the kaizen
# signal). Everything else (files_touched, verification, ...) is session
# bookkeeping, not improvement signal.
LEARNING_FIELDS = ("created_at", "mission", "problems", "landmines", "decisions")


def _last_record_created_at(log_path: Path) -> str | None:
    if not log_path.exists():
        return None
    try:
        lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return None
    if not lines:
        return None
    try:
        return json.loads(lines[-1]).get("created_at")
    except json.JSONDecodeError:
        return None


def _distil(handoff: dict[str, object]) -> dict[str, object]:
    return {key: handoff.get(key) for key in LEARNING_FIELDS if handoff.get(key)}


def run(repo_root: str) -> int:
    directory = C.handoff_dir(repo_root)
    handoff_json = directory / C.HANDOFF_JSON_NAME
    if not handoff_json.is_file():
        sys.stderr.write(f"no handoff json at {handoff_json}\n")
        return 1
    try:
        handoff = json.loads(handoff_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"unreadable handoff json: {exc}\n")
        return 1
    if not isinstance(handoff, dict):
        sys.stderr.write("handoff json is not an object\n")
        return 1

    record = _distil(handoff)
    if not record.get("problems") and not record.get("landmines"):
        # Nothing worth mining; do not pollute the signal log.
        sys.stderr.write("no learnings (problems/landmines) to log\n")
        return 0

    log_path = directory / C.LEARNINGS_LOG_NAME
    created_at = record.get("created_at")
    if created_at and created_at == _last_record_created_at(log_path):
        sys.stderr.write("learnings for this handoff already logged (idempotent)\n")
        return 0

    try:
        directory.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        sys.stderr.write(f"could not append to learnings log: {exc}\n")
        return 1
    sys.stderr.write(f"logged learnings to {log_path}\n")
    return 0


def main() -> int:
    repo_root = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    return run(repo_root)


if __name__ == "__main__":
    sys.exit(main())
