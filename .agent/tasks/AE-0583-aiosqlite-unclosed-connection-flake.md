# AE-0583 — Backend tests flake on an unclosed aiosqlite connection (unraisable ResourceWarning)

Status: Intake
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa
Branch: TBD
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

The backend suite passes deterministically: no test fails because some earlier test left an aiosqlite connection or
an asyncio event loop unclosed, without skipping a test or loosening the warning filter.

## Problem

Under pytest's unraisable-exception handling, a `ResourceWarning: <aiosqlite.core.Connection ...> was deleted before
being closed` (raised from `Connection.__del__` when the garbage collector runs) becomes a
`PytestUnraisableExceptionWarning`. That error is charged to whichever test happens to be running, so a test that
did nothing wrong errors at setup. Seen:

- 2026-10-30 / 2026-10-31, local full `gate-capture.sh backend` runs: `test_publishing_safety_net.py::TestBlogPostCrud::test_get_returns_200`
  (setup error, twice), `test_blog_sections_api_ae0423` (once).
- 2026-10-31 CI, PR #315 run 41202058535: `test_blog_dashboard_ae0411.py::TestCreateSlug::test_duplicate_given_slug_is_clear_409`
  (setup error; 7870 passed). The rerun passed.
- Running `tests/unit/scripts_ci/` on its own (on main as well) ends with an `ExceptionGroup` of unraisable
  `BaseEventLoop.__del__` warnings, charged to a passing test (e.g. `test_meta_ads_env_ae0579`).

Every failing test passes when run alone.

## Scope

- Find the fixtures/tests that open aiosqlite engines or connections (and event loops in `tests/unit/scripts_ci/`)
  without disposing/closing them, e.g. with `tracemalloc` (`PYTHONTRACEMALLOC=20`) on a full run, and close them
  (`await engine.dispose()`, `async with`, loop close) at their source.
- Prove it: a full backend run and a `tests/unit/scripts_ci/`-only run end with no unraisable warning.

## Non-Goals

- No `skip` / `xfail`, no change to the warning filters or `-p no:unraisableexception`.

## Acceptance Criteria

- [ ] AC1 The leaking fixtures are found and close their connections/loops.
- [ ] AC2 `pytest tests/unit/scripts_ci/` alone exits 0.
- [ ] AC3 Three consecutive full `gate-capture.sh backend` runs show no unraisable-warning error.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None. Related: AE-0577 (another load flake).

## Progress Log

### 2026-10-31

Ticket created from the occurrences above.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
