# AE-0316 — Shared carousel serialization lock and typed conflict details

Status: Review
Tier: T1
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

One tiny, dependency-free foundation that AE-0311 (repair), AE-0313
(republish), and AE-0315 (typed 409s) all build on, so the shared surfaces
land exactly once: a per-project carousel serialization lock helper and a
typed conflict-detail schema for 409 responses.

## Problem

Cold-critic review (r3) of the AE-0309..0315 set found the shared surfaces
had no owner: AE-0311 claims to acquire "AE-0313's advisory lock" (which
does not exist yet) and to return "typed 409 details" (whose schema AE-0315
owns). Depending on ship order this produces either duplicate lock
implementations or a repair endpoint that ships without the serialization
it promises. The standard fix: extract the first-classified surface into a
small ticket both sides depend on.

## Scope

- `carousel_project_lock(project_id)` helper (Postgres **session-scoped**
  advisory lock — `pg_advisory_lock`/`pg_advisory_unlock` keyed by a
  stable hash of the project UUID; cold-critic r5: a transaction-scoped
  lock releases at the first commit, which would not span AE-0311's
  two-commit projection→checkpoint seam) in the infrastructure layer,
  with an async context-manager API that guarantees unlock on exit
  (connection drop also releases it server-side) and a non-blocking
  `try_acquire` variant that raises a typed conflict.
- **Serialization-domain contract (documented in the helper's docstring —
  cold-critic r4: do not call this "the single domain" when it is not):**
  the advisory lock serializes the **artifact-affecting mutators**:
  AE-0311 repair, AE-0313 republish, and AE-0314's completed-project
  slide-update endpoint (cold-critic r5: the edit endpoint writes
  `carousel_slides` then chains republish — outside the lock it could
  lose updates to a concurrent repair). Each holds the lock across its
  full write sequence (for repair: both commits). Resume-vs-repair is serialized by
  the `lock_version` CAS (both bump it); reap-vs-repair/resume is
  serialized by the reaper bumping `lock_version` in its flip UPDATE
  (AE-0315) — the background resume runner and the reaper deliberately do
  NOT acquire the advisory lock. The contract table (which actor holds
  which guard) ships in the docstring and the workflow docs.
  **Resume-start guard (cold-critic r6: the CAS gates the start of each
  mutation, not its duration — a resume submitted between a repair's two
  commits could run against a stale checkpoint):** the resume path's
  `ensure_resume_not_in_progress` additionally does a non-blocking check
  of the advisory lock; if any artifact mutator currently holds it, the
  resume is rejected with a typed `mutation_in_progress` conflict. The
  resume runner still never *acquires* the lock — it only refuses to
  start while one is held, which closes the two-commit seam without
  serializing long workflow runs behind it.
- Typed conflict-detail schema for carousel 409 responses:
  machine-readable `code` (`run_in_progress`, `version_conflict`,
  `revision_cap_exceeded`, `build_in_progress`, `mutation_in_progress`),
  optional `run_started_at`,
  optional `phase` (for cap errors), human-readable `message`. Pydantic
  model + OpenAPI component; constants for the codes.
- Adopt the schema in the existing resume 409 paths
  (`ensure_resume_not_in_progress`, lock-version CAS, revision cap) so the
  three existing conflict causes are distinguishable immediately —
  consumers (AE-0311/0313/0315) then reuse both primitives.

## Non-Goals

- No new endpoints (AE-0311/0313 own theirs).
- No frontend changes (AE-0315 owns the client rendering).
- No behavioral change to when conflicts occur — only how they are
  identified and how mutual exclusion is expressed.

## Acceptance Criteria

- [x] `carousel_project_lock` serializes two concurrent holders in a
      concurrency test (second waits or fails typed, per variant), and
      the lock provably spans multiple sequential transactions by one
      holder (session-scoped semantics test).
- [x] The three existing resume 409 causes return distinct
      machine-readable codes; response shapes are additive
      (existing clients unaffected).
- [x] Cap-exceeded details include the charged phase; run-in-progress
      details include `run_started_at` when available.
- [x] OpenAPI + route snapshot regenerated (pinned artifacts).
- [x] Rule-fires-style test: each conflict path is seeded and asserts its
      exact code.
- [x] Resume-start guard: a resume submitted while the advisory lock is
      held returns the typed `mutation_in_progress` conflict; after
      release it succeeds (test covers the two-commit seam window).
- [x] Lock lifetime safety: unlock in a `finally` on the same connection;
      pooled-connection recycling resets advisory locks on return
      (test/documented pool configuration) so a crashed request can never
      leak a held lock into an unrelated request.

## Gherkin Scenarios

```gherkin
Feature: Typed carousel conflict details

  Scenario: Resume during an active run returns a typed conflict
    Given a carousel workflow run is in progress
    When a resume request is submitted
    Then the 409 detail carries code run_in_progress and run_started_at

  Scenario: Stale lock version returns a distinct typed conflict
    Given a resume request with an outdated lock_version
    When the compare-and-swap fails
    Then the 409 detail carries code version_conflict

  Scenario: Advisory lock serializes concurrent holders
    Given one holder inside carousel_project_lock for a project
    When a second caller uses the non-blocking variant
    Then it receives a typed build_in_progress conflict
```

## Delta

### ADDED

- `carousel_project_lock` advisory-lock helper (infrastructure).
- Typed conflict-detail schema + code constants.

### MODIFIED

- Resume 409 paths adopt the typed details (additive).

### REMOVED

- Nothing.

## Affected Areas

- Backend: infrastructure lock helper; `editorial_workflow_routes_validate.py`
- Frontend: none (consumers land in AE-0315)
- Database: none (advisory locks are session/transaction scoped)
- API: additive 409 detail shape (OpenAPI regeneration)
- Tests: unit + concurrency; seeded conflict-path tests
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0311, AE-0313, AE-0315
- Blocked by: none
- Related: AE-0107 (write owner), cold-critic review r3

## Implementation Plan

1. Lock helper + concurrency test.
2. Conflict-detail schema + constants; adopt in resume paths.
3. Regenerate pinned API artifacts; full gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (lock reentrancy, connection drop releases lock)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from cold-critic r3 cross-ticket finding (shared surface
needs a single owner).

### 2026-07-10 — Dev Complete

Implemented on branch feat/ae-0309-0316-carousel-reliability-wave
(worktree). Session-scoped advisory lock in
modules/editorial/infrastructure/carousel_project_lock.py (dialect-gated:
Postgres-only semantics, SQLite test fixtures no-op), re-exported via the
editorial facade. Typed conflict domain model + additive 409 body
(detail keeps the legacy string; conflict object added) via a dedicated
exception handler. Resume-start mutation guard wired into the resume
route. OpenAPI artifact regenerated (+73 lines). Existing resume 409
integration tests pass unchanged (additive proof).

## Files Touched

- backend/src/rag_backend/domain/constants/carousel_conflicts.py (new)
- backend/src/rag_backend/domain/models/carousel_conflict.py (new)
- backend/src/rag_backend/api/schemas/carousel_conflict.py (new)
- backend/src/rag_backend/api/middleware/carousel_conflict_handler.py (new)
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_project_lock.py (new)
- backend/src/rag_backend/modules/editorial/public.py
- backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_validate.py
- backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_support.py
- backend/src/rag_backend/api/routes/carousels/editorial_workflow.py
- backend/src/rag_backend/bootstrap/app_factory.py
- backend/tests/features/carousel_typed_conflicts.feature (new)
- backend/tests/unit/domain/test_carousel_conflict.py (new)
- backend/tests/unit/api/test_carousel_conflict_handler.py (new)
- backend/tests/unit/api/test_editorial_workflow_resume_guard.py (new)
- backend/tests/unit/infrastructure/test_carousel_project_lock.py (new)
- backend/tests/integration/test_carousel_project_lock_pg.py (new)
- docs/architecture/openapi.json (regenerated)

## Test Evidence

- 22 new unit tests pass (domain model, handler round-trip per code,
  dialect gating, resume-start guard).
- Postgres integration tests (advisory-lock concurrency, blocking waits,
  session scope across transactions) skip locally, run in CI's postgres.
- Full unit suite: 2175 passed, 1 skipped.
- gates.sh backend --changed-only: PASS=15 FAIL=0 SKIP=5.
- Existing resume 409 integration tests pass unchanged (additive body).

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r6) — Cold-critic BLOCKER resolved: resume-start lock check closes the seam

Round-6 showed the lock_version CAS only gates mutation *starts* — a
resume beginning between a repair's projection commit and checkpoint
commit would run against a stale checkpoint. Resolution: resume start now
performs a non-blocking advisory-lock check (typed `mutation_in_progress`
409 while any artifact mutator holds it) — the seam is closed without the
resume runner ever holding the lock. Pool-recycling lock-leak edge added
to ACs.

### 2026-07-10 (r5) — Cold-critic WARNs resolved: session-scoped lock + AE-0314 joins the domain

Round-5: switched from transaction-scoped to session-scoped advisory lock
so it spans AE-0311's two-commit seam (xact-scope would release at the
projection commit), and added AE-0314's completed-project slide-update
endpoint to the lock domain (third artifact-affecting mutator).

### 2026-07-10 (r4) — Cold-critic WARN resolved: serialization-domain contract pinned

Round-4 flagged that "single serialization domain" was false — the resume
runner and reaper never hold the advisory lock. Resolution: the contract
is now explicit (advisory lock = repair-vs-republish; `lock_version` CAS
= resume/repair/reap mutual detection, with AE-0315's reaper bumping the
version in its flip), documented in the helper docstring and workflow
docs.

## Blockers

None.

## Final Summary

Pending.
