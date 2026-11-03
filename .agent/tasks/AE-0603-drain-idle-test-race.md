# AE-0603 — The drain idle test no longer races the whole-second clock

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Tests
Owner: Lead
Branch: fix/ae-0603-drain-idle-test-race
Created: 2026-11-03
Updated: 2026-11-03

## Goal

`test_an_idle_worker_is_stopped_at_once` (AE-0598) passes or fails on what the drain does, not on where a
second boundary falls.

## Problem

On PR #340 the backend gate failed on one test, 8597 passed:

```
FAILED tests/unit/scripts_ci/test_drain_generation_worker_ae0598.py::test_an_idle_worker_is_stopped_at_once
AssertionError: assert 'idle after 0s' in 'DRAIN: flag set, waiting up to 30s for the job in flight\nDRAIN: generation-worker idle after 1s\n'
```

`scripts/deploy/drain-generation-worker.sh` reports the wait as `$((SECONDS - started))`. `$SECONDS` counts
whole seconds, so a drain of a few milliseconds reads `1s` whenever a second boundary falls between
`started=$SECONDS` and the first idle check; on a loaded runner the check's Python start alone can cross
one. The production deploy of ba6b4de43 logged `idle after 1s` for the same reason. The script is right;
the test pinned a value the clock cannot promise.

## Scope

- The idle test proves "stopped at once" by one idle check and a run shorter than one poll interval
  (20 s), and matches the idle line without pinning the second count.
- A counter-case test: a worker busy on the first check is polled again and the run lasts at least one
  poll interval, so both "at once" guards would fail on it. The busy file is removed once the second idle
  check is logged (not on a timer), so a slow first check still sees the worker busy.

## Non-Goals

- No change to the drain script, the deploy, any gate, timeout, marker or skip.

## Acceptance Criteria

- [x] The idle test no longer asserts `idle after 0s`; it asserts one idle check, no warning, the idle
  line, and an elapsed time under the 20 s poll.
- [x] A busy-first-check test asserts at least two idle checks and an elapsed time of at least one poll.
- [x] The drain test file passes 3 runs in a row and 6 runs in parallel.

## Classification

Test-only fix, "unit tests suffice" (root CLAUDE.md, AE-0153): (a) no public or user-visible behavior
change, no source, script or deploy change; (b) the busy-first-check test is the seeded counter-case
proving the guards fire; (c) affected gates: backend format, lint, test; (d) reviewer sign-off on the
no-`.feature` classification is requested on the PR. The tests keep citing the existing AE-0598 scenario
"The deploy waits until the worker is idle, then stops it".

## Repro Steps

1. Run the drain test file on a loaded machine, or start the idle test just before a second boundary.
2. The script prints `idle after 1s` and the old assertion fails.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0598 (merged, #339).

## Progress Log

### 2026-11-03 07:40

Ticket created from the #340 backend gate failure; fix written and stress-run.

## Files Touched

- `backend/tests/unit/scripts_ci/test_drain_generation_worker_ae0598.py`

## Test Evidence

See `.agent/reports/AE-0603.dev-summary.md`: the drain test file passes 3 runs in a row and 6 in
parallel; the light backend gates pass individually; the full suite and mutation run in CI.
