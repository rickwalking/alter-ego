# AE-0332 — fix the ci test-isolation flake class (global db engine swap + event-loop scope)

Status: Ready
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Make `Backend Quality Gates` deterministic: the same commit must not be red on
one run and green on a re-run. Remove the shared-global test fixtures that let
one test module poison every module that runs after it.

## Problem

The push-to-`main` run for the PR #87 merge (2026-09-15) failed
`Backend Quality Gates` with **2 blog-post integration failures + 16
`RuntimeError: Event loop is closed`**. A re-run of the *same commit* was green
on all 11 jobs including mutation. Nothing in the tree changed — the failure is
ordering-dependent, so CI red currently carries no information and the team is
trained to re-run rather than investigate. That is how a real regression gets
waved through.

Two concrete mechanisms were identified:

1. **Global engine swap.** `backend/tests/integration/test_blog_post_management_ae0296.py`
   reaches into module state and assigns the process-wide engine directly:

   ```python
   import rag_backend.infrastructure.database.config as db_config
   engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
   db_config.c_engine = engine          # line 54 — global mutation
   ...
   db_config.c_engine = None            # line 62
   await close_db()
   await engine.dispose()
   ```

   `c_engine` is a module-level global (`infrastructure/database/config.py:17`)
   read by `get_session_maker()` and `close_db()`. The fixture's teardown calls
   `close_db()` *after* nulling `c_engine`, so `close_db()`'s `if c_engine:`
   guard is already false and the dispose ordering depends on which object each
   caller captured. Any other test (or app-level singleton) that captured a
   sessionmaker bound to the previous engine now holds a handle to an engine
   attached to a **closed event loop** — hence the 16 `Event loop is closed`
   errors, which appear in *unrelated* modules.

2. **Fixture loop scope.** The `client` fixture is an `async` function-scoped
   fixture, but the engine it creates is bound to whatever loop anyio/pytest-asyncio
   gives that test. Session- or module-scoped consumers outlive that loop.

A third, previously observed member of the same class: the **slowapi limiter**
keeps process-global rate-limit state that leaks across test modules, so a test
that exhausts a limit can fail a later, unrelated test.

## Scope

- `backend/tests/integration/test_blog_post_management_ae0296.py`: stop assigning
  `db_config.c_engine` directly; take the engine/session through a FastAPI
  dependency override (`app.dependency_overrides`) or an explicit
  inject-and-restore helper that is exception-safe and restores the *previous*
  value rather than `None`.
- A shared test helper (e.g. `backend/tests/conftest.py` or
  `backend/tests/support/db.py`) that owns "give me an isolated in-memory DB for
  this test" so no test module hand-rolls the swap again.
- Audit every other test that writes `db_config.c_engine` (or any
  `rag_backend.*` module global) and route it through the same helper.
- Reset the slowapi limiter state between test modules (autouse fixture).
- A **guard test** that fails if a test module assigns `db_config.c_engine`
  directly (grep/AST check over `backend/tests/`), so the class cannot return.

## Non-Goals

- Making the integration suite run against real Postgres (separate concern).
- Re-tuning `pytest-asyncio` / `anyio` loop scope globally for the whole suite —
  change only what these fixtures need.
- The Alembic two-heads problem (AE-0207 follow-up, unrelated).

## Acceptance Criteria

- [ ] `test_blog_post_management_ae0296.py` no longer assigns
      `db_config.c_engine`; isolation comes from a dependency override or a
      restore-previous-value helper.
- [ ] Teardown is exception-safe (a failing test still restores global state)
      and disposes the engine **before** clearing the reference.
- [ ] Running the full backend suite in a **randomized module order**
      (`pytest -p no:randomly` off / `pytest --random-order` or an explicit
      reversed-order run) is green 3 consecutive times.
- [ ] Zero `RuntimeError: Event loop is closed` in the full-suite output.
- [ ] Slowapi limiter state is reset between modules; a test that exhausts a
      rate limit does not affect a later module.
- [ ] A guard test FIRES on a seeded violation (a test file that assigns
      `db_config.c_engine`) — asserts non-zero exit, per AE-0180.
- [ ] `bash scripts/ci/gate-capture.sh backend` green; GATES_JSON pasted into the
      dev summary.

## Gherkin Scenarios

```gherkin
Feature: Backend test isolation

  Scenario: A module that needs its own database does not poison later modules
    Given the blog-post integration module has run with an in-memory database
    When any later test module opens a database session
    Then it uses the process engine that existed before that module ran
    And no "Event loop is closed" error is raised

  Scenario: Suite order does not decide the result
    Given the full backend suite
    When it runs with the module order reversed
    Then the result is identical to the forward-order run

  Scenario: The guard catches a re-introduced global swap
    Given a test file that assigns db_config.c_engine directly
    When the isolation guard runs
    Then it exits non-zero and names the offending file
```

## Affected Areas

- Backend: test fixtures only (no production source change expected)
- Frontend: no
- Database: no
- API: no
- Tests: yes — fixtures, new shared helper, new guard test
- Docs: `docs/guides/qa-checkpoints.md` note on the isolation rule
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: trustworthy CI signal for every later ticket
- Blocked by: none
- Related: AE-0296 (the module that introduced the swap), AE-0180 (rule-fires standard)

## Implementation Plan

1. Reproduce: run the backend suite with reversed module order and capture the
   16 `Event loop is closed` errors plus the 2 blog-post failures.
2. Add `backend/tests/support/db.py` with an `isolated_sqlite_app()` helper that
   uses `app.dependency_overrides` and restores the previous global on exit
   (try/finally), disposing before clearing.
3. Port `test_blog_post_management_ae0296.py` to the helper.
4. Grep for other `c_engine` writers; port them too.
5. Add the autouse slowapi limiter reset.
6. Add the guard test with a seeded-violation fixture proving it fires.
7. Run the suite 3× in randomized order; capture gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (fixture raises mid-test; nested overrides)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330/0331 session handoff. Root cause located at
`test_blog_post_management_ae0296.py:54,62` against the `c_engine` global in
`infrastructure/database/config.py:17`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
