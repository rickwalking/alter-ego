# AE-0322 — gate-capture dirty-tree guard: fail on uncommitted in-scope source, gate_proof blocks dirty>0 without waiver

Status: Review
Tier: T1
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: feat/kaizen-wave-ae0322-0328
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

- [x] `gate-capture.sh <scope>` exits 2 and names the files when untracked or
      modified source files exist under the scope's dirs (seeded-violation test:
      create an untracked seeded `.py`/`.ts` in scope → exit 2; AE-0180).
- [x] With `GATE_CAPTURE_ALLOW_DIRTY=1` the gate runs, the exit is the gate's own
      exit, and the echoed GATES_JSON line carries `"dirty":N` with the correct N.
- [x] Clean tree behaviour is byte-identical to today (control test).
- [x] `gate_proof.py` blocks a transition whose GATES_JSON has `"dirty">0` and no
      `DIRTY_WAIVER:` line in the dev-summary (seeded test), and allows it when the
      waiver line is present (control test).
- [x] Existing gate-proof tests still pass; docs updated (CLAUDE.md gate-run loop
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

### 2026-07-22 — development complete (wave feat/kaizen-wave-ae0322-0328)

Implemented: scoped git status --porcelain -uall pre-flight (backend/scripts | frontend/src/scripts | superset) filtered to source extensions; default exit 2, GATE_CAPTURE_ALLOW_DIRTY=1 stamps "dirty":N into the echoed GATES_JSON; gate_proof.py blocks transitions on dirty>0 without a DIRTY_WAIVER: line (horizontal-whitespace-only regex), warns when waived; CLAUDE.md gate-loop section documents it. Commit ccfc8793.

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P1). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

- scripts/ci/gate-capture.sh
- scripts/agent_tasks/constants.py
- scripts/agent_tasks/gate_proof.py
- backend/tests/unit/scripts_ci/test_gate_capture_dirty_guard.py
- backend/tests/unit/agent_tasks/test_gate_proof.py
- CLAUDE.md

## Test Evidence

uv run pytest tests/unit/scripts_ci/test_gate_capture_dirty_guard.py tests/unit/agent_tasks/test_gate_proof.py tests/unit/scripts_ci/test_gate_capture.py -> 25 passed (untracked/modified source -> exit 2 naming files; ALLOW_DIRTY=1 stamps dirty:N; clean tree byte-identical; non-source + out-of-scope ignored; failing-gate exit preserved; gate_proof blocks dirty>0 without waiver, warns with waiver, empty waiver blocks).

## QA Report

Pending.

## Blockers

None.
