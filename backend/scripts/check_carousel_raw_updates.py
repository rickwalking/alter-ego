#!/usr/bin/env python3
"""Lint gate: ban NEW raw UPDATEs against the run-fenced carousel tables (AE-0315).

The run-epoch fence (layer a) lives at the SQLAlchemy flush boundary, so it
cannot see SQLAlchemy Core ``update()`` statements or textual SQL. Every such
site must carry an explicit epoch guard and be enumerated in the AE-0315
write-site survey — this checker fails on any raw UPDATE against
``carousel_projects`` / ``carousel_slides`` outside the allowlist below.

Run standalone (``python scripts/check_carousel_raw_updates.py``) or through
the rule-fires unit test (``tests/unit/scripts_ci/test_carousel_raw_update_gate.py``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Files allowed to issue raw UPDATEs against the guarded tables. Each entry is
# enumerated (with its guard) in .agent/reports/AE-0315.write-site-survey.md §2.
ALLOWED_RAW_UPDATE_FILES: frozenset[str] = frozenset({
    # Resume/build lock_version CAS — request-scoped, 409-gated; reaper bumps
    # lock_version so post-reap CAS holders fail on version (survey #18).
    "application/services/optimistic_lock_service.py",
    # activate_build CAS — carries the explicit epoch check (survey #17).
    "infrastructure/database/carousel_artifact_build_repository.py",
    # Reaper flip — tick-owned CAS on phase_status + run_epoch (survey #20).
    "infrastructure/database/carousel_run_reaper.py",
    # Heartbeat write — self-fencing WHERE on run_epoch (survey #19).
    "modules/editorial/infrastructure/carousel_run_progress.py",
    # AE-0320 phase-drift convergence — tick-owned CAS on phase_status=failed,
    # bumping lock_version + run_epoch like the reaper flip it mirrors.
    "infrastructure/database/carousel_drift_reconciler.py",
})

_ORM_CORE_UPDATE_RE = re.compile(r"update\(\s*Carousel(Project|Slide)Model\b")
_TEXTUAL_UPDATE_RE = re.compile(r"UPDATE\s+carousel_(projects|slides)\b", re.IGNORECASE)


def scan_for_raw_updates(src_root: Path) -> list[str]:
    """Return ``path:line`` violation entries under ``src_root``."""
    violations: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        rel = path.relative_to(src_root).as_posix()
        if rel in ALLOWED_RAW_UPDATE_FILES:
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if _ORM_CORE_UPDATE_RE.search(line) or _TEXTUAL_UPDATE_RE.search(line):
                violations.append(f"{rel}:{line_number}: {line.strip()}")
    return violations


def main() -> int:
    """CLI entry point; exit 1 on any un-allowlisted raw UPDATE."""
    src_root = Path(__file__).resolve().parents[1] / "src" / "rag_backend"
    violations = scan_for_raw_updates(src_root)
    if not violations:
        print("carousel raw-update gate: OK")
        return 0
    print(
        "carousel raw-update gate: NEW raw UPDATE(s) against fenced tables "
        "(add an explicit epoch guard, enumerate the site in the AE-0315 "
        "write-site survey, then allowlist it here):"
    )
    for violation in violations:
        print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
