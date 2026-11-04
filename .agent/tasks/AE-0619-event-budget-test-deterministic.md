# AE-0619 — The cancelled event write test made deterministic

Status: Dev Complete
Tier: T1
Priority: High
Type: Chore
Area: Tests
Owner: Lead
Branch: fix/ae-0619-event-budget-test-deterministic
Created: 2026-11-04
Updated: 2026-11-04

## Goal

`test_cancelled_event_writes_leave_the_workflow_intact` (added by AE-0608) passes or fails on what the recorder
does, not on memory addresses or garbage-collector timing. No skip, retry, budget change, timeout raise or loosened
assertion.

## Problem

After #354 merged, the test failed on two unrelated PRs, each on its merge with main 64b9169a. Main's own run passed.

- #358, run 41876531090, job 126738059182, `backend / Test & Coverage`: `assert [UUID('bc2d87...')] == []`. An event
  the recorder reported as dropped was stored.
- #359, run 41874435344, job 126749103897, `backend / Mutation`, clean-tests phase:
  `(sqlite3.OperationalError) database is locked` from the workflow's `mark_waiting` commit, after a first commit had
  already failed the same way 5 s earlier. mutmut aborted before checking any mutant.

### Root cause 1: arming by `id()` (the stored event, #358)

The test held each event insert in SQLite's trace callback. It installed the callback lazily, on the first event
insert of each connection, and remembered armed connections by `id()` of SQLAlchemy's connection wrapper. A held
insert is cancelled, so SQLAlchemy invalidates that connection and reconnects for the next write. Once the old
wrapper is freed, CPython can give the new wrapper the same address. The test then took the new connection for an
armed one and never installed the callback, so that insert ran unheld, finished inside the budget, and committed.

Caught with a probe on main + #358, Python 3.12 and coverage (the CI setup), with random event-loop stalls: in three
of the stored-event runs the probe printed a new connection whose wrapper id equals an earlier, invalidated one,
with a different driver connection, followed by an insert that completed (`UNHELD-DONE w=7e2424b3cf70
d=7e2424448260 traced=[..., '7e2424b3cf70']`) and a cancel that landed on the commit. Rate: 2 of 64 runs, then 3 of
192 with the probe. The same stalls on main alone gave no unheld insert in 160 runs, so #358 makes the reuse more
likely, but the defect is the test's: an `id()` is unique only among live objects, and #358's own code does not touch
the recorder or its connections.

### Root cause 2: a closed connection that keeps its read lock (#359)

The recorder's first statement is the run lookup, `session.get(GenerationRunModel, ...)`. When the budget cancels a
write during that read, SQLAlchemy invalidates and closes the connection, but the cancelled cursor stays alive in
the exception's reference cycle until the garbage collector runs. SQLite defers closing a connection that still has
a live statement (`sqlite3_close_v2`), and in rollback-journal mode that statement keeps its SHARED lock. The
workflow's next commit, on the other connection, needs EXCLUSIVE, waits out the 5 s busy timeout and fails with
`database is locked`, exactly the two 5 s gaps in the #359 log.

Evidence:

- With random event-loop stalls on main: 10 of 96 runs `database is locked`. Every one follows a cancel during the
  run lookup (`ERR CancelledError stmt=SELECT`), then the workflow's commits fail 5 s apart.
- The same 96 runs with a garbage collection every 200 ms in a side thread: 0 locked.
- Plain `sqlite3`, no SQLAlchemy: a closed connection with a stepped `SELECT` cursor still referenced makes another
  connection's commit fail with `database is locked` in rollback-journal mode, and succeed in WAL mode.
- #359's settle hook is not a cause. It wraps `pytest_runtest_call` and only changes timing: the failing stack runs
  through it, and the failure reproduces without it.

The AE-0608 decision log said a second connection would not hit `database is locked`. That held for the runs it
made, which never cancelled a write during its read. It does not hold in general.

## Scope

- `backend/tests/integration/carousel_consolidation/` only: `conftest.py`, the new `event_connections.py`, and
  `test_event_recorder_connection.py`.

## Non-Goals

- Production code. Production runs on Postgres, where a reader never blocks a writer and a cancelled asyncpg query
  holds no file lock, so neither cause exists there. The 100 ms budget stays as it is.
- The shared `StaticPool` connection the workflow, the outbox relay and the workers use in this suite
  (`cannot commit transaction - SQL statements in progress` from the relay). It predates AE-0608 and did not fail a
  test here.

## Acceptance Criteria

- [x] Every connection the recorder opens carries the hold from the moment it is opened. Nothing is keyed by `id()`.
- [x] A held recorder statement never completes: the test asserts `completed == 0`, which an unheld insert fails.
- [x] A cancelled run lookup cannot lock the workflow: `test_a_cancelled_event_read_does_not_lock_the_workflow`
  fails 3 of 3 in rollback-journal mode with `database is locked` and passes in WAL mode.
- [x] The budget, the busy timeout and every assertion are unchanged or stricter. No skip, retry or sleep added.
- [x] 50 runs of the file alone, 50 of the suite, and the file and the suite with #359 merged, all green.
- [x] Stress runs that reproduced both failures no longer produce either.

## Classification

CI and test tooling, "unit tests suffice" (root CLAUDE.md, AE-0153):

- (a) No public or user-visible behavior change: nothing under `backend/src`, `pyproject.toml`, `uv.lock` or the CI
  workflows changes.
- (b) Seeded-violation tests: `test_a_cancelled_event_read_does_not_lock_the_workflow` fails 3 of 3 with WAL turned
  off. The `completed == 0` assertion fails on any insert that escapes the hold, the stored-event mechanism.
- (c) Affected gates: `backend:test`, `backend:mutation` (its clean-tests phase runs this suite), and backend format,
  lint, comments, docstrings, gherkin-refs, duplication and dead-code.
- (d) Reviewer or QA sign-off on the no-`.feature` classification is requested on the PR. Both tests cite the
  existing scenario "Recorder timeout preserves authoritative generation state".

## Decision Log

- The hold is installed by `EventConnections` inside the shielded connect, before the connection reaches
  SQLAlchemy, through `trace_statements`. That removes the `id()` lookup and also the extra await the old lazy arming
  added inside the budget, where a cancel left the connection marked armed without SQLAlchemy invalidating it.
- The hold stays three budgets long. It is not padding: any hold longer than the budget works, because the timer is
  due before the statement can return, and asyncio runs the timer before the task's wakeup even when the loop is late.
- The suite's SQLite file runs in WAL mode, asserted at setup. In WAL a reader never blocks a writer, as in
  Postgres, so a cursor that outlives its connection cannot fail the workflow. The alternative was closing every
  cursor before each close, which needs a subclass of `aiosqlite.Connection` and its private constructor, and still
  misses SQLAlchemy's force-close path.
- `test_a_cancelled_event_read_does_not_lock_the_workflow` disables the garbage collector while the revise runs, so
  the cancelled cursor survives every time and the test does not depend on when a collection happens. It re-enables
  it in `finally`.
- `completed` counts only statements on the recorder's own connections (`EventConnections.owns`), because the
  workflow reads `generation_runs` too.
- Under artificial stalls of up to 150 ms before half of all statements, 2 of 192 runs (main + #358) and 2 of 96
  (main) failed `held > 0`: every
  write was cancelled before reaching its insert, so the case under test did not happen. That needs a stall longer
  than the whole budget before each of the five writes; no run without the artificial stalls showed it.

## Progress Log

### 2026-11-04 18:00

Both CI logs read. Reproduced both failures locally with probes and event-loop stalls, on main, main + #358 and
main + #359.

### 2026-11-04 21:00

Fix in place: arming at open, WAL, the completed-statement check and the cancelled-read test. Evidence below.

## Test Evidence

Environment: `DATABASE_URL=postgresql+asyncpg://test:test@127.0.0.1:55433/rag_test_ae0619`, test secrets as in the
dev summary. "Stalls" means a local-only pytest plugin, kept outside the repository, that sleeps a random 0 to 150 ms
in the event loop before half of all statements.

| Run | Before | After |
|---|---|---|
| Stalls, main + #358, Python 3.12, `--cov`, 64 or 192 runs | 2 of 64 stored; 3 of 192 stored | 0 of 192 stored, 0 locked, 0 unheld inserts |
| Stalls, main, 96 runs | 10 locked, 1 `held > 0` | 0 locked, 0 stored, 0 unheld inserts, 2 `held > 0` |
| Cancelled run lookup, WAL off | | 3 of 3 `database is locked` |
| File alone, 50 runs (`uv run pytest tests/integration/carousel_consolidation/test_event_recorder_connection.py`) | | 50 of 50 green |
| File with #359 merged, 50 runs, same command | | 50 of 50 green |
| Suite, 50 runs (`uv run pytest tests/integration/carousel_consolidation`) | | 50 of 50, 98 passed each |
| Suite with #359 merged, 25 runs, same command | | 25 of 25, 98 passed each |

## Files Touched

- `backend/tests/integration/carousel_consolidation/conftest.py`
- `backend/tests/integration/carousel_consolidation/event_connections.py` (new)
- `backend/tests/integration/carousel_consolidation/test_event_recorder_connection.py`
- `.agent/reports/AE-0619.dev-summary.md` (new)

## QA Report

Not run yet: the no-`.feature` classification sign-off is requested on the PR.

## Blockers

None.

## Follow-ups

- The suite's workflow, outbox relay and workers share one `StaticPool` connection, so one session's commit can
  meet another's open statement (`cannot commit transaction - SQL statements in progress`). Not a failure today.

## Final Summary

Two test-only causes, both fixed at the root: connections armed by a reusable `id()`, and a cancelled read lock that
outlives its connection in rollback-journal mode. No production change, no limit touched.
