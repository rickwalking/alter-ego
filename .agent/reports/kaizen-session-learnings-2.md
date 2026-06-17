# Kaizen Report — session-learnings-2 (2026-06-17)
Mode: sweep (retrospective) | Scope: dev→QA loop + parallel-agent repo hygiene

## This session
Completed AE-0183 (dead deps 12→0), AE-0184 (use-auth→Query + no-fetch rule),
AE-0185 (max-lines calibration 116→42 + ratchet). dev→QA converged first pass:
eslint errors 0, 884 tests pass, seeded rule verified, zero suppressions.

## Learning Classes (ranked)

| # | Learning | Evidence | Severity |
|---|----------|----------|----------|
| L1 | In a multi-agent repo, branch/PR base state churns constantly — must RE-DERIVE the trunk before any branch/PR work | base branch `phase-8-kaizen-class-b` deleted mid-task; "merged PR #28" not in main (async still 32); a stale "241 behind" reading vanished after fetch | High |
| L2 | ESLint flat-config: same-key rules REPLACE (not merge) across overlapping `files` blocks — adding a `no-restricted-syntax` hooks rule silently drops the global one | subagent had to re-declare the useEffect guard in the hooks block | High (already ticketed: AE-0179) |
| L3 | `validate_ticket.py` Review gate requires BOTH `.dev-summary.md` AND `.qa.md` per ticket | move_ticket → Review failed twice until both existed | Info (process) |
| L4 | Well-scoped tickets + (eslint+tsc+tests) QA converge first-pass repeatedly | AE-0177 and AE-0183/0184/0185 both zero-rework | Info (positive) |

## Proposals
- **P1 (process):** before multi-PR work, `git fetch --prune` + re-derive trunk/HEAD;
  never trust a prior base. → memory saved (no ticket needed).
- **L2** already enforced by **AE-0179** (eslint-flat-config guard) — this session is
  independent confirmation it's a real, recurring footgun. No new ticket.

## Rejected (would loosen): none.
