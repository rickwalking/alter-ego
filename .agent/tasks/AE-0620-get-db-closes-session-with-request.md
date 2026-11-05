# AE-0620 — Close the request session when a handler raises, so no connection leaks after AE-0614

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Bug
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0620-aiosqlite-leak-after-ae0614
Kanban Card: TBD
Created: 2026-11-05
Updated: 2026-11-05

## Goal

A request's database session and connection are released when the request ends, however it ends. The remaining source
of the `aiosqlite` `ResourceWarning` flake is removed at its cause, and nothing suppresses the warning.

## Problem

Run 41939599716 (PR #360 at a6c973bd, which already contains AE-0614) failed `backend / Test & Coverage` on
`test_change_own_password_pg_ae0511.py::test_a_wrong_current_password_leaves_the_stored_user_unchanged` with
`ResourceWarning: <aiosqlite.core.Connection ...> was deleted before being closed`. That test is a victim.

## Root Cause

A production lifecycle bug in `get_db`, unchanged since the dependency was written:

```python
async for session in get_session():
    yield session
```

When a handler raises, FastAPI throws the exception into `get_db`. It surfaces at the `yield`, and an `async for` does
not close its iterator on the way out. So the inner `get_session` generator stays suspended inside its
`async with session_maker()`, holding the session and its connection until the garbage collector or the loop's
`shutdown_asyncgens` reaches it. This hits every `get_db` route that raises (401, 404, 409, 500). On Postgres the effect
is a connection held past the end of the request, with its rollback deferred too.

The test failure then follows the AE-0614 end state from a different opener, one the relay settle wrapper does not
cover: `engine.dispose()` swaps the pool while the connection is still checked out, the late close returns it to the old
pool, nothing can reach that pool, and the garbage collector finalizes the connection during an unrelated test.

## Evidence

All runs used a throwaway `-p` tracer that was not committed. Same 88 files, the tests before the victim in the CI order
of run 41939599716, one core, no delay:

| Measure | Old code | Fixed |
| --- | --- | --- |
| Tests | 741 passed, 1 skipped | 741 passed, 1 skipped |
| `dispose()` with a connection still checked out | 7 | 0 |
| `get_session` finalized by the garbage-collector hook | 192 | 0 |
| Tests ending with `AsyncSession.close` still pending | 29 | 0 |
| Connections deleted while open | 0 | 0 |

The 7 are `test_unknown_post_is_404`, `test_retry_is_refused_unless_the_run_failed`,
`test_stale_if_match_on_publish_is_409`, `test_unpublish_returns_to_draft`, `test_cancel_needs_approved`,
`test_restoring_a_published_caption_is_refused` and `test_keyset_pages_are_bounded_and_stable_during_inserts`, all on
file SQLite with a queue pool, at fixture teardown.

A standalone script (raising route on `get_db`, file SQLite, `dispose()` straight after the response, then
`asyncio.run` ending the loop) gives the exact CI warning every time on the old code: 1 connection checked out after
the response. On the fixed code: 0 checked out, no warning.

Ruled out:

- Relay overlapping `dispose()`: `_relay_pending` does start during teardown in 9 tests, from the first worker tick in
  the `carousel_consolidation` lifespan, but 0 relays were in flight at any dispose, with 0.01 s per aiosqlite call in
  the one test traced and 0.05 s across 6 tests before that run timed out.
- Cancelled aiosqlite connect, and SQLAlchemy terminate: both end in `stop()`, which closes the connection (read in
  aiosqlite 0.22.1 and SQLAlchemy 2.0.49).
- The CI environment: same Python and Postgres service, no extra services. The difference found is `--cov`.

**Limit of this evidence:** the deletion never happened inside the real suite on this host, in plain runs, with delays,
under low GC thresholds on the password tests, or under `--cov` on the 7 tests. Those tests leave the checked-out state,
but here the late close appears to be cancelled and terminated rather than checked in to the old pool. That explanation
is inferred, not traced. So the link to the CI failure is the identical warning reproduced through this path, the
precondition measured in real tests that run before the victim, and no other opener in any run. A delayed subset run
(0.02 s per call) timed out at 90 minutes, about 45% through, and is partial. The tracer never ran on a CI runner. One
green CI run proves little for a flake; the real check is that it stops recurring.

## Scope

- `get_db` opens and closes the session itself.
- `.feature` and regression tests for success, refusal, crash, a direct throw, and the leak itself.

## Non-Goals

- `lifespan` calling `close_db()` without draining relays: still open, see Follow-ups. No run showed it leak.
- `get_session`, which closes correctly when FastAPI uses it directly.
- `pytest.ini`, `pyproject.toml`, the CI pytest command, and unraisable-exception handling are unchanged.

## Acceptance Criteria

- [x] The opener is identified with evidence, and the limit of that evidence is recorded.
- [x] `get_db` releases its connection on success, HTTP error, crash and a direct throw.
- [x] The fix closes the connection. No `filterwarnings`, `-W ignore`, added `gc.collect()` outside the regression
  test's own proof, retry, rerun, skip, xfail or timeout change.
- [x] The regression tests fail on the old code: 4 of 5 failed. The success path passed, as expected.
- [x] CI pytest command and pytest settings are unchanged.
- [ ] CI is green on the PR, mutation included.

## Gherkin Scenarios

See `backend/tests/features/request_session_closed_with_the_request_ae0620.feature`.

```gherkin
Feature: A request's database session closes with the request

  Scenario: A handler that refuses the request releases its connection
    Given a route that reads through get_db and then raises an HTTP error
    When the request is refused
    Then no connection is checked out when the response has returned
```

## Delta

### ADDED

- `backend/tests/features/request_session_closed_with_the_request_ae0620.feature`
- `backend/tests/unit/api/test_get_db_closes_session_ae0620.py`

### MODIFIED

- `get_db` opens the session with `async with` instead of delegating through `async for`. Its return annotation is now
  `AsyncIterator[AsyncSession]`.

### REMOVED

- None.

## Affected Areas

- Backend: `api/dependencies/database.py`
- Frontend: none
- Database: none (no schema change; connections are released earlier)
- API: no contract change
- Tests: new unit tests
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0614, AE-0608

## Implementation Plan

1. Find the opener. 2. `.feature`, then tests that fail on the old code. 3. Fix. 4. Compare the tracer before and after.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-05

Opener found, fixed and compared. A first delayed run was stopped on host memory and resumed on the owner's instruction.

## Files Touched

- `backend/src/rag_backend/api/dependencies/database.py`
- `backend/tests/features/request_session_closed_with_the_request_ae0620.feature` (new)
- `backend/tests/unit/api/test_get_db_closes_session_ae0620.py` (new)
- `.agent/tasks/AE-0620-get-db-closes-session-with-request.md` (new)
- `.agent/reports/AE-0620.dev-summary.md` (new)

## Test Evidence

See Evidence above. Cheap gates green: format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, docstrings,
dead-code, gherkin-refs, comments, integrity, duplication. Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

- Behaviour-changing, so it has a `.feature`: a production lifecycle bug, not test tooling.
- `get_db` opens the session itself rather than wrapping `get_session` in `aclosing`: `get_session` is annotated
  `-> AsyncSession`, so `aclosing` would not type-check without changing that annotation for every direct user. No test
  patches `get_session` through this module or overrides either dependency.
- Fixed at the opener rather than extending the settle wrapper, which would have hidden a production bug.
- The AE-0614 settle wrapper stays: it covers relays, a separate path.

## Blockers

None.

## Follow-ups

- `lifespan` calls `close_db()` without draining relays (`app_factory.py`), as AE-0614 noted.
- The first worker tick in the `carousel_consolidation` client starts on the session loop and resumes at teardown, so it
  commits and starts a relay after the settle wrapper has run. No leak seen.

## Final Summary

`get_db` now closes its session when a handler raises. Awaiting CI and the lead's heavy gate.
