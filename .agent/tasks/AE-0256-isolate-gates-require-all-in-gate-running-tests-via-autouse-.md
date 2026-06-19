# AE-0256 — isolate gates_require_all in gate-running tests via autouse conftest fixture

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Stop gate-running tests from inheriting CI's **`GATES_REQUIRE_ALL=1`** and silently changing
behavior (green local / red CI), by isolating that one env var in an autouse fixture instead
of relying on each test author remembering a manual `env.pop`.

> Scope note (per architect review): this isolates **`GATES_REQUIRE_ALL` specifically**. It is
> NOT a general "gate tests never inherit any CI env var" guarantee — other CI vars (`CI`,
> `GITHUB_ACTIONS`, …) are out of scope. The fixture docstring must say so to avoid a false
> sense of completeness.

## Problem

`scripts/ci/gates.sh` honors `GATES_REQUIRE_ALL`; CI sets it to `1`, which flips a
tool-missing SKIP into a FAIL. Tests that invoke gates.sh inherit that env, so a test
asserting a SKIP passes locally (var unset) but fails in CI (var set). This bit twice —
AE-0239 (`test_dead_files_gate_skips_when_knip_hidden`, fixed via `env.pop("GATES_REQUIRE_ALL")`,
commit `6ed44618`) and a prior occurrence. Each fix was a per-test manual pop; the class
recurs whenever a new gate test forgets it.

Source: `.agent/reports/kaizen-session-2026-06-19.plan.md` (failure class #3) +
`.skeptical-review.md` (P3 INFO — critic concurs the autouse-fixture approach is sound).

## Scope

- An autouse pytest fixture in the gate-tests' `conftest.py` (the package containing the
  tests that invoke `scripts/ci/gates.sh`) that pops `GATES_REQUIRE_ALL` unless a test opts
  in explicitly.
- A test proving the fixture isolates the var.

## Non-Goals

- No change to `gates.sh` behavior or CI's `GATES_REQUIRE_ALL=1`. Explicit "no user-visible
  behavior change; CI/tooling" classification per CLAUDE.md AE-0153.

## Acceptance Criteria

- [ ] An autouse fixture in the gate-tests' conftest removes `GATES_REQUIRE_ALL` from the
      environment for each test by default; a test can opt back in explicitly (e.g. via a
      marker or monkeypatch within the test body).
- [ ] A test proves the fixture isolates the var: with `GATES_REQUIRE_ALL=1` set in the
      process env, a gate test that expects SKIP still observes SKIP (not FAIL).
- [ ] The previously-manual `env.pop` in the AE-0239 test is removed (now redundant) and
      that test still passes both locally and with `GATES_REQUIRE_ALL=1` set.
- [ ] The fixture's docstring explicitly states it isolates **only** `GATES_REQUIRE_ALL` and
      that other CI env vars are NOT handled (architect-review framing fix).

## Gherkin Scenarios

```gherkin
Feature: gate-running tests are isolated from GATES_REQUIRE_ALL

  Scenario: a SKIP-expecting gate test passes even when CI's env var is set
    Given GATES_REQUIRE_ALL=1 is present in the process environment
      And a gate test that expects a tool-missing SKIP
    When the test runs under the autouse isolation fixture
    Then the gate reports SKIP and the test passes
```

## Affected Areas

- Tests: backend gate-tests conftest.py + isolation test; AE-0239 test cleanup
- Docs: —

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0239 (the second occurrence + manual fix); kaizen-session-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (opt-in path; var set vs unset)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic finding (plan-round, accepted)
- INFO "conftest boundary not tested" — critic concurs the standard pytest conftest
  mechanism covers the directory; AC includes an explicit isolation test so the boundary is
  proven rather than assumed.

### 2026-06-19 — external architect review of the ticket (round 2, accepted)
- WARN "'structurally impossible' overpromises; only one env var handled" — accepted; Goal
  reworded to scope to `GATES_REQUIRE_ALL`; fixture-docstring scope note added as an AC.
- INFO "existing AE-0239 test override still works after fixture" — confirmed by the critic;
  no change needed.

## Blockers

None.

## Final Summary

Pending.
