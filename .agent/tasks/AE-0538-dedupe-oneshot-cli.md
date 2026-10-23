# AE-0538 — Fix-forward: the archived_at one-shot uses the shared CLI runner (main red on Duplication)

Status: In Development
Tier: T1
Priority: High
Type: Chore
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0538-dedupe-oneshot-cli
Created: 2026-10-23
Updated: 2026-10-23

## Goal

`main` is green again on `backend / Duplication`.

## Problem

After #258 (AE-0527) merged, `backend / Duplication` fails on `main`: jscpd finds 0.41% duplicated Python
lines, over the 0.4% threshold. The new clone is `scripts/carousel_archived_at.py` lines 57-76 against
`scripts/palette_timestamptz.py` (the own-engine runner and `main`), 19 lines.

## Scope

- `scripts/cli_support.py`: `run_on_own_engine(run)` runs a coroutine on a dedicated engine and disposes of it.
- `scripts/carousel_archived_at.py` uses `run_guarded_cli` and `run_on_own_engine` instead of its own copy.

## Non-Goals

- Refactoring the other one-shots (their clones are older and under the threshold).
- Changing the threshold.

## Acceptance Criteria

- [x] `bash scripts/ci/gates.sh backend:duplication` passes (0.39%; the `carousel_archived_at` clone is gone).
- [x] The one-shot keeps its flags, output and exit codes (0 ok, 1 verify failed, 2 usage).
- [x] The dedicated engine is disposed of also when the run raises.

## No-`.feature` classification (pure refactor, CI fix)

- (a) No public or user-visible behavior change: same CLI flags, messages and exit codes; the deploy step
  is unchanged.
- (b) Seeded-violation test: not a new gate or rule; the existing duplication gate is the check, and it
  fails on `main` before this change (0.41%) and passes after (0.39%).
- (c) Affected gates: `backend:duplication` (fixed), `backend:test` (new unit tests).
- (d) Reviewer/QA sign-off on the no-`.feature` classification: requested on the PR.

## Affected Areas

- Backend: `scripts/cli_support.py`, `scripts/carousel_archived_at.py`. Tests:
  `tests/unit/scripts/test_one_shot_engine_ae0538.py`.
- Frontend, database, API: none.

## Dependencies

- Blocked by: none. Follows #258.
- Blocks: every PR while `main` is red.

## Progress Log

### 2026-10-23

`backend / Duplication` red on `main` at 4f364fb68 (#258). Reproduced locally (0.41%) and on the parent
commit (0.40%, green). Moved the own-engine runner into `cli_support`; the gate is at 0.39%.

## Files Touched

- `backend/src/rag_backend/scripts/cli_support.py`, `backend/src/rag_backend/scripts/carousel_archived_at.py`,
  `backend/tests/unit/scripts/test_one_shot_engine_ae0538.py`.

## Test Evidence

One-shot unit tests (CLI, end to end on SQLite, Postgres integration) and the new runner tests green. Gates:
`.agent/reports/AE-0538.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-10-23 — Fix forward with a dedupe rather than raising the threshold (gates are never loosened).

## Blockers

None.
