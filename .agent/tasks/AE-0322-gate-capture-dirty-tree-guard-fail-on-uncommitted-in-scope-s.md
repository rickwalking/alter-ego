# AE-0322 — gate-capture dirty-tree guard: fail on uncommitted in-scope source, gate_proof blocks dirty>0 without waiver

Status: In Development
Tier: T1
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

Diff-based gates can never silently return a false green on uncommitted/untracked
work: `gate-capture.sh` refuses (or loudly stamps) a dirty in-scope tree, and the
move-time guard blocks transitions on an unwaived dirty run.

## Problem

Kaizen failure class FC-1 (`.agent/reports/kaizen-session-2026-07-22.signal.md`).
Diff-based gates (`lint-diff`, strict-diff, integrity) compare committed HEAD vs
`origin/main`, so untracked files are invisible. Incident: AE-0301 gate-capture
reported "No changed Python files" while the commit-to-be added a `.py` file —
external QA later caught 2 real ruff violations hiding behind that green
(learnings-log 2026-07-08). A second session landmine (2026-06-24) documents the
same class for the integrity scan. Today the only defense is tribal knowledge
("commit first, then gate-capture"). `scripts/ci/gate-capture.sh` has no
working-tree pre-flight (verified 2026-07-22).

## Scope

- `scripts/ci/gate-capture.sh`: pre-flight `git status --porcelain` scoped to the
  gate's source dirs (backend/ for backend, frontend/src for frontend, plus
  scripts/). Untracked or modified source files in scope →
  - default: exit 2 with a DIRTY-TREE error naming the files;
  - `GATE_CAPTURE_ALLOW_DIRTY=1`: loud warning + stamp `"dirty":N` into the echoed
    GATES_JSON line.
- `scripts/agent_tasks/gate_proof.py`: a GATES_JSON with `"dirty">0` BLOCKS the
  Dev Complete/Review transition unless the dev-summary carries a `DIRTY_WAIVER:`
  line naming the out-of-scope files and why they belong to other sessions
  (observability+friction ratchet, same design as AE-0258; CI on the committed
  tree stays the final authority).

## Non-Goals

- Do not change gates.sh itself or any individual gate's diff base.
- Do not block on dirty files OUTSIDE the gate's scope dirs (multi-session
  working trees are the documented normal state of this repo).
- Do not refactor unrelated code.

## Acceptance Criteria

- [ ] `gate-capture.sh <scope>` exits 2 and names the files when untracked or
      modified source files exist under the scope's dirs (seeded-violation test:
      create an untracked seeded `.py`/`.ts` in scope → exit 2; AE-0180).
- [ ] With `GATE_CAPTURE_ALLOW_DIRTY=1` the gate runs, the exit is the gate's own
      exit, and the echoed GATES_JSON line carries `"dirty":N` with the correct N.
- [ ] Clean tree behaviour is byte-identical to today (control test).
- [ ] `gate_proof.py` blocks a transition whose GATES_JSON has `"dirty">0` and no
      `DIRTY_WAIVER:` line in the dev-summary (seeded test), and allows it when the
      waiver line is present (control test).
- [ ] Existing gate-proof tests still pass; docs updated (CLAUDE.md gate-run loop
      section gains one line on the dirty guard + waiver).

## Repro Steps

1. On a branch, create a new `.py` file with a ruff violation; do NOT `git add`.
2. Run `bash scripts/ci/gate-capture.sh backend` → today: lint-diff reports "No
   changed Python files", overall green. False green.

## Affected Areas

- [x] Backend (tests under backend/tests/unit/scripts_ci/)
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Decision Log

- Cold-critic BLOCKER-1 (2026-07-22, `.agent/reports/kaizen-session-2026-07-22.skeptical-review.md`):
  an env-var override with no consumer is a silent down-ratchet. Resolved: the
  named consumer is `gate_proof.py` (the AE-0258 move-time parser), which hard-blocks
  `dirty>0` without a `DIRTY_WAIVER:` line.

## Progress Log

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P1). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
