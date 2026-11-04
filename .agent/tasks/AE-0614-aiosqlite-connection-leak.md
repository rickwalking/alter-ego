# AE-0614 — Close the aiosqlite connection that leaked into later tests

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Chore
Area: Tests
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0614-aiosqlite-connection-leak
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

`backend / Test & Coverage` stops failing at random on an unclosed `aiosqlite` connection, because the connection gets
closed. Nothing suppresses the warning.

## Problem

The job sometimes fails with one error, at the setup of whichever test is running when the garbage collector finalizes
the connection:

`ResourceWarning: <aiosqlite.core.Connection object at 0x...> was deleted before being closed`, raised as
`pytest.PytestUnraisableExceptionWarning`.

So the failing test is a victim. Known instances: run 41794303155 (`test_chat_stream.py`), run 41587274170, run
41202058535, and notes on `test_change_own_password_pg_ae0511`, `test_publishing_safety_net`,
`test_blog_sections_api_ae0423`, `test_blog_dashboard_ae0411` and `test_autopilot_topic_intake`. AE-0608 looked for the
opener and did not find it.

## Root Cause

The opener is `_relay_pending`, the post-commit outbox relay that `workflow_event_service._schedule_relay` starts as a
background task. It reads through the global `db_config.c_engine`. Async tests run on a function-scoped loop and
fixtures on the session loop (`asyncio_default_fixture_loop_scope = session`), so a relay can outlive its test body:

1. The test body returns and its loop stops, freezing the relay mid-query with a connection checked out.
2. The fixture disposes the engine on the session loop. `dispose()` replaces the pool.
3. pytest-asyncio closes the test loop and cancels the relay. Its connection is checked in to the old pool, which
   nothing can reach or close.
4. The garbage collector finalizes that connection later, during an unrelated test.

It depends on timing because the relay must still be inside its session when the test returns. A plain run almost
never hits that window on this host, which is why neither a plain run here nor the AE-0608 tracer showed it. A slower
CI runner can.

A tracer that keeps its records in a weak map would also miss the opener: the weak reference is already cleared when
`__del__` runs, so the first version of this tracer logged 20 `DEL_OPEN` records with no opener. Storing the record on
the instance fixed that. Whether this is what hid it from the AE-0608 tracer is not confirmed.

## Evidence

All runs used a throwaway `-p` plugin that was not committed. It records the opener of each connection, calls
`gc.collect()` after each test, and reports any connection deleted while open or still open after its test.

| Run | Scope | Harness | Result |
| --- | --- | --- | --- |
| Baseline | `tests/integration` | plain | 1607 passed, 1 skipped; only the session `test_engine` stays open |
| Connect delay | first 800 tests | one core, 50 ms connect | 744 passed, 1 skipped, 56 `Event loop is closed` errors |
| Name the task | 3 files | one core, 50 ms connect | 21 of 21 records name `_relay_pending` |
| Reproduce | 3 files | one core, 50 ms per relay query | 16 passed, 26 errors, the exact CI `ResourceWarning`; 21 of 21 `DEL_OPEN` records name `_relay_pending` at `outbox_relay.py:111`, opened in the test's `call` phase |
| Fixed | same 3 files | both delays | 29 passed, no tracer events |
| Fixed | `tests/integration` | both delays | 1605 passed, 1 skipped, 3 failed; no leak records |
| Fixed | `tests/unit`, `tests/property` | plain | 7218 passed, 1 skipped, 1 failed; the only `DEL_OPEN` is the seeded test |

The 4 failures are not caused by this ticket:

- `test_check_env_permissions.py::test_fires_on_wrong_owner_expectation` fails the same way with and without the fix.
  It expects a wrong owner, and this host runs as root.
- `test_background_resume_does_not_wait_for_a_hanging_exporter`,
  `test_background_resume_publishes_review_required_for_outline_gate` and `test_parallel_requests_at_cap_minus_one`
  fail only under the delays, with and without the fix, twice each. They pass in a plain run with and without it.
  Without the fix the same harness also adds teardown errors on `test_failed_write_keeps_the_reservation`.

**Limit of this evidence:** the tracer never ran on a CI runner. The link to the CI failures is the identical warning
and path reproduced locally, plus no other opener in any run above. The unit tree was not run with the delays. No CI
job can prove a negative for a flake, so the check on this ticket is that the failure stops recurring.

## Scope

- Finish outbox relays after the test body and before fixture teardown, in the unit and integration trees.
- A seeded regression test that reproduces the leak through the real relay and engine.
- A wiring test in each tree.

## Non-Goals

- No production change: see the follow-up on `lifespan`.
- No change to `pyproject.toml`, `pytest.ini`, the CI pytest command or unraisable-exception handling.
- `tests/conftest.py` is left alone, so the `no_outbox_relay` docstring is unchanged.

## Acceptance Criteria

- [x] The opener is identified with evidence, not inferred.
- [x] The fix closes the connection. There is no `filterwarnings`, `-W ignore`, `gc.collect()` outside the regression
  test's own proof, retry, rerun, skip, xfail or timeout change.
- [x] A regression test fails on the old lifecycle: `test_a_relay_frozen_past_dispose_leaks_its_connection` shows the
  leak firing, and both `test_a_relay_left_running_is_finished_before_teardown` tests error when the hook is unwired.
- [x] CI pytest command and pytest settings are unchanged.
- [ ] CI is green on the PR, mutation included.

## Classification

Test tooling, "unit tests suffice" (root CLAUDE.md, AE-0153):

- (a) No public or user-visible behaviour change: nothing under `backend/src` changes.
- (b) Seeded-violation test: `test_a_relay_frozen_past_dispose_leaks_its_connection` runs the real relay and an
  aiosqlite engine through the failing lifecycle and asserts the `ResourceWarning` fires exactly once.
- (c) Affected gates: `backend:test`, plus backend comments, strict-diff, lint-diff, duplication, integrity and
  gherkin-refs.
- (d) Reviewer or QA sign-off on the no-`.feature` classification is requested on the PR.

## Delta

### ADDED

- `settle_outbox_relays` and its `pytest_runtest_call` wrapper.
- `tests/unit/conftest.py`, which wires the wrapper for the unit tree.
- Regression and wiring tests.

### MODIFIED

- `tests/integration/conftest.py` wires the wrapper for the integration tree.

### REMOVED

- None.

## Affected Areas

- Backend: tests only
- Frontend: none
- Database: none
- API: none
- Tests: `backend/tests/support`, `backend/tests/unit`, `backend/tests/integration`
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0608 (its follow-up on the unclosed connection is answered here)

## Implementation Plan

1. Find the opener with a tracer and widened race windows.
2. Reproduce the CI warning.
3. Finish relays before fixture teardown.
4. Prove it with a seeded test and a wiring test in each tree.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Opener found and reproduced, fix and tests written, PR opened.

## Files Touched

- `backend/tests/support/outbox_relay_settle.py` (new)
- `backend/tests/support/outbox_relay_settle_wiring.py` (new)
- `backend/tests/unit/conftest.py` (new)
- `backend/tests/integration/conftest.py`
- `backend/tests/unit/test_outbox_relay_settle_ae0614.py` (new)
- `backend/tests/unit/test_outbox_relay_hook_ae0614.py` (new)
- `backend/tests/integration/test_outbox_relay_hook_ae0614.py` (new)
- `.agent/tasks/AE-0614-aiosqlite-connection-leak.md` (new)
- `.agent/reports/AE-0614.dev-summary.md` (new)

## Test Evidence

See Evidence above. Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

- A `pytest_runtest_call` wrapper, not an autouse fixture. An autouse fixture is set up first and so torn down last,
  after the engine is disposed, which is the order that causes the leak.
- Relays run to completion rather than being cancelled early. Cancelling mid-connect drops the raw `sqlite3` connection
  without closing it, so completing is what really closes what was opened.
- Relays are settled per loop, because one can sit on the test loop or, when a fixture committed it, on the session
  loop. `drain_pending_publishes` cannot await both, so the helper reads `_inflight_publishes` directly.
- The wrapper is re-exported from the unit and integration conftests. `tests/conftest.py` would cover every tree in one
  place but is in open work on PR #354, and a plugin flag would change the pytest settings.
- No change under `backend/src`: the leak needs a test loop closing under a live engine, which production does not have.

## Follow-ups

- `lifespan` calls `close_db()` without draining relays (`app_factory.py:185-186`), although the
  `drain_pending_publishes` docstring says "tests and shutdown"; nothing in `src` calls it. On shutdown an in-flight
  relay can hit the same disposed pool. The impact is small because the process is exiting and rows are retried
  at-least-once, so it is left for a separate ticket: either drain there or correct the docstring.
- `tests/property`, `tests/e2e` and `tests/load` are not wired. The property tree produced no relay leak in the run
  above; `tests/e2e` and `tests/load` were not run.
- Once PR #354 merges, the two conftest re-exports could move to `tests/conftest.py`.
