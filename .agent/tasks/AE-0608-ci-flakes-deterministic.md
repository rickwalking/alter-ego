# AE-0608 — Four recurring CI flakes made deterministic

Status: In Development
Tier: T2
Priority: Medium
Type: Chore
Area: Tests
Owner: Lead
Branch: fix/ae-0608-ci-flakes-deterministic
Created: 2026-11-04
Updated: 2026-11-04

## Goal

Four recurring test failures stop depending on machine load, the network, the date or test order. Each gets a
root cause and a fix for that cause, with no limit raised, no retry and nothing skipped.

## Problem

### 1. Generation-event writes raced their 100 ms budget

`test_carousel_parent_cascade_removes_events` failed on main at d647cfcc (run 41711321676, attempt 1; the log has
`generation_event_store_failed ... TimeoutError`, and attempt 2 passed). `record_generation_event` wraps each write
in `asyncio.timeout(EVENT_WRITE_TIMEOUT_SECONDS)` (0.1 s) and returns `False` when it runs over. That is the right
production contract for best-effort diagnostics. The tests asserted the return value, so "the runner was busy for
100 ms" read as a failure. The race was wider than the reported test: the keyset test in the same file,
`test_stored_rows_and_api_exclude_sensitive_failure_content` and `test_daily_revive_becomes_a_visible_queued_event`
all needed a write to finish inside the budget, and `test_nullable_autopilot_mismatch_is_rejected` could pass on a
timeout instead of on the rejection it exists to prove.

### 2. The frontend comment gate spent its time in a parser it did not need

`check-comments.mjs` called `parser.parseForESLint`, which builds an ESTree and runs scope analysis for every file
only to read `ast.comments`. Over 1,274 files that took 5.2 to 6.3 s and 550 MB, so a loaded runner reached the 10 s
vitest limit on "passes on the real source tree". Of the time measured on `src/`, importing `typescript-eslint`
cost 0.8 s and `parseForESLint` 4.4 s, against 0.6 s for `ts.createSourceFile` alone.

### 3. A test's fake Langfuse keys leaked into every later app startup

`monitoring_langfuse.init_langfuse` calls `os.environ.setdefault` for the Langfuse keys. The fixture in
`test_langfuse_cloud_ae0545.py` removes those variables with `monkeypatch.delenv(..., raising=False)`, which records
nothing when the variable is absent, so the fake keys stayed in `os.environ` after the test. Every later app startup
read them through `Settings`, built a real client and exported spans to Langfuse Cloud, which answered
`Failed to export spans batch code: 401, reason: Unauthorized`. The startup auth check made a real call as well
(`langfuse_auth_failed reason=401`). Natural collection order hides this, since the integration tests start the app
before the unit test runs. The mutation job runs tests in its own order, which is why the line appeared 23 times in
that job (run 41733730478) and never in `Test & Coverage`.

### 4. Import-time clocks and a shared-database count

- `test_a_stale_run_is_resumed_once_and_not_too_early` seeds rows from `_NOW`, fixed at import, while
  `revive_stale` reads `SystemClock`. Once a run lasts over 40 minutes, the "20-minute-old" run is past the
  one-hour threshold and is resumed too early.
- `test_the_same_carousels_alert_when_not_archived` dates its failed row with the import-time `_NOW`, while
  `WorkflowFailureAlertService` reads the real clock, so the row falls out of the failure window on a long run.
- `test_timeout_auto_reject_clears_leftover_run_columns` counts a table-wide sweep on the session-wide SQLite engine.
  After `test_workflow_timeout_repository.py` it sees that file's stale rows too and returns 3 instead of 1.

## Scope

- Tests and tooling only, as listed under Files Touched.
- `frontend/scripts/check-comments.mjs` reads comments through a lighter parser, with the policy unchanged.

## Non-Goals

- The production 100 ms budget, tracing setup and `monitoring_langfuse.init_langfuse` stay as they are.
- Replacing the other import-time clocks. They feed injected clocks, or production code that takes the time as an
  argument, so they do not reach the real clock.

## Acceptance Criteria

- [x] No test outcome depends on a generation-event write finishing inside the budget, proven with a zero budget.
- [x] `EVENT_WRITE_TIMEOUT_SECONDS` is unchanged and the production path still runs in these tests.
- [x] The comment gate reports the same comments as before on the real tree and takes under half the time.
- [x] The 10 s vitest limit is unchanged.
- [x] No exporter is built in the test run, in the order that used to build one, with a test proving it.
- [x] Production tracing code is unchanged.
- [x] The two clock tests pass with import-time clocks hours stale.
- [x] `test_carousel_run_guard` passes alone and in every order tried with the files that share its table.
- [ ] CI is green, mutation included.

## Classification

CI and test tooling, "unit tests suffice" (root CLAUDE.md, AE-0153):

- (a) No public or user-visible behavior change: nothing under `backend/src` changes, and the comment policy accepts
  and rejects exactly what it did.
- (b) Seeded-violation tests: `check-comments.test.ts` keeps its `FAILS on a seeded ...` cases and adds literals that
  must not read as comments. `test_the_same_client_exports_when_the_switch_is_gone` proves the exporter check fires.
  `test_the_write_is_stored_however_slow_against_the_budget` confirms the zero budget really drops the wait.
- (c) Affected gates: `frontend:lint` (`lint:comments`, `lint:knip`), `frontend:test`, `backend:test`, and backend
  format, lint, comments, docstrings and gherkin-refs.
- (d) Reviewer or QA sign-off on the no-`.feature` classification is requested on the PR. The tests keep citing their
  existing scenarios.

## Decision Log

- Item 1 uses `SettledEventRecorder`, a test wrapper around the real recorder. It is not a disguised timeout raise:
  the budget stays 100 ms and still applies to the production call, and the test's result no longer depends on any
  time limit, longer or shorter. The write is shielded from the cancel, and the test waits for what the store actually
  answered, so a write that fails or is refused still fails the test. No production seam was needed, because
  `GenerationEventRecorder` is already injected. Calling the recorder directly would have dropped the production
  path from these tests.
- Item 2 adds `ts-api-utils` 2.5.0 as a direct devDependency, the version already installed through
  `typescript-eslint`, because knip rejects an unlisted import. Reading comments from `ts.createSourceFile` and
  `iterateComments` gave the same 4,307 comments as `parseForESLint` on all 1,273 files compared. One difference:
  a file with a syntax error no longer crashes this gate. `tsc` and ESLint still report it.
- Item 3 forces the values in `tests/conftest.py` rather than defaulting them, and blanks the keys rather than
  deleting them: an empty value outranks `.env` and defeats the `setdefault` leak, so the fixture in
  `test_langfuse_cloud_ae0545.py` did not need changing.
- Item 4 injects the clock for `revive_stale` by replacing `queue_bridge.SystemClock` in that test, since the
  production method takes no clock. The archive test dates its failed row when the test runs, because the service
  under test reads the real clock. The run-guard test gets its own empty database and keeps `== 1`.
- No static rule against module-level clocks was added: most of those constants are safe, so a rule would need an
  allowlist, and the import-time clock run below answers the question directly.

## Progress Log

### 2026-11-04 00:00

Ticket created. Root causes reproduced on an untouched checkout of 549c4b46 before any fix.

## Files Touched

- `backend/tests/conftest.py`
- `backend/tests/integration/generation_event_support.py` (new)
- `backend/tests/integration/test_carousel_generation_log_ae0556.py`
- `backend/tests/integration/test_daily_recovery_events_ae0556.py`
- `backend/tests/integration/test_daily_recovery_scan_ae0524.py`
- `backend/tests/integration/test_generation_events_pg_ae0556.py`
- `backend/tests/unit/application/test_carousel_archive_ae0527.py`
- `backend/tests/unit/infrastructure/test_carousel_run_guard.py`
- `backend/tests/unit/test_hermetic_tracing_ae0608.py` (new)
- `frontend/package.json`, `frontend/package-lock.json`
- `frontend/scripts/check-comments.mjs`
- `frontend/src/scripts/check-comments.test.ts`

## Test Evidence

Pending; see `.agent/reports/AE-0608.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.

## Final Summary

Pending.
