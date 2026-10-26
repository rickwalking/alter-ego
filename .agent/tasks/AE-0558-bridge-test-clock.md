# AE-0558 — The generation bridge test seeds runs at the current time

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Branch: ae-0558-bridge-test-clock
Created: 2026-10-26
Updated: 2026-10-26

## Goal

`backend / Test & Coverage` is green again on main and on every PR.

## Problem

`tests/integration/test_generation_bridge_ae0522.py` seeds autopilot runs with `created_at`/`updated_at` at a
fixed `2026-10-23 12:00 UTC`, while `AutopilotQueueBridge.sweep` reads the system clock. The owner review
expires after `OWNER_REVIEW_EXPIRY_HOURS = 72`, so from 2026-10-26 12:00 UTC the sweep expires the seeded
`awaiting_owner` run. `test_bridge_facts_and_no_step_for_a_parked_run` then fails with `assert 1 == 0` on
every run, whatever the PR changes. #291 was green earlier the same day; #292 failed at 17:15 UTC.

## Scope

- `_seed` stamps the run with the current time.

## Non-Goals

- Changing the bridge, the sweep or the expiry.
- The other test in the file that injects a fixed clock into the editorial driver (it does not depend on
  the wall clock).

## Acceptance Criteria

- [x] AC1 The bridge integration tests pass whatever the current date is.

## Classification

Test-only fix, no `.feature`. (a) No public or user-visible behavior changes; only the seed time of a test
fixture changes. (b) There is no seeded-violation test: this is a time-dependent test fixture, not a gate or
rule. The failing test is its own regression check and fails on origin/main today. (c) Affected gates:
backend:test. (d) QA sign-off: `.agent/reports/AE-0558.qa.md`.

## Repro Steps

1. On origin/main, after 2026-10-26 12:00 UTC: `uv run pytest tests/integration/test_generation_bridge_ae0522.py`.
2. `test_bridge_facts_and_no_step_for_a_parked_run` fails with `assert 1 == 0` at `bridge.sweep()`.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None. Unblocks every backend PR, #292 (AE-0555) among them.

## Progress Log

### 2026-10-26 17:30

Found by AE-0555's CI. Reproduced locally on origin/main (1 failed, 6 passed); with the fix, 7 passed.

## Files Touched

- `backend/tests/integration/test_generation_bridge_ae0522.py`
- `.agent/tasks/AE-0558-bridge-test-clock.md`
- `.agent/reports/AE-0558.dev-summary.md`
- `.agent/reports/AE-0558.qa.md`

## Test Evidence

- origin/main: 1 failed (`assert 1 == 0`), 6 passed.
- This branch: 7 passed.
- No assertion or expectation lines removed.

## QA Report

`.agent/reports/AE-0558.qa.md`.

## Blockers

None.
