# AE-0490 — Admin password reset and self change-password return 500

Status: Review
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0490-password-reset-500
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

"Redefinir senha" on /admin/users and `POST /api/auth/change-password` succeed: the admin gets a working temporary
password, and a user's new password replaces the old one.

## Problem

Dashboard QA (2026-10-22, Users area): "Redefinir senha" returns 500 "Database Error". Both flows only change
`hashed_password` and then call `PostgresUserRepository.update`. That re-assigns an unchanged `updated_at`, so the
column's `onupdate=func.now()` sets it in the database and the flush expires the attribute. `model.to_entity()` then
lazy-loads `updated_at` inside the async session → `MissingGreenlet` (a `SQLAlchemyError`) → the error handler's
500 "Database Error". Role/active edits worked only because `set_role`/`activate` bump `updated_at` first.

The defect was already known: two integration tests and two `.feature` scenarios pinned the 500 as a baseline
("Change/Reset password currently 500s due to onupdate lazy-load defect").

## Scope

- `PostgresUserRepository.update` refreshes the model after the flush, so database-set columns are loaded with an
  awaited query before mapping to the entity.
- The pinned-500 tests and scenarios are replaced by the intended contract (204/200 + log-in checks).
- A repository test on real Postgres (no mocks) covers a password-only update and an explicit `updated_at`.

## Non-Goals

- Forced password change on next login, email reset links (Pedro's Q10; AE-0511).
- Self-service change-password UI (AE-0511).

## Acceptance Criteria

- [x] Given an admin on /admin/users, When they click "Redefinir senha" on another user, Then the API returns 200
      with the temporary password, the user can log in with it, and the old password no longer works.
- [x] Given a logged-in user, When `POST /api/auth/change-password` is called with the right current password, Then
      it returns 204, the new password logs in, and the old password no longer works.
- [x] Given the fix, Then a repository-level test with a real async Postgres session (not a mock) covers an `update`
      where only `hashed_password` changes, and the returned and stored `updated_at` match.
- [x] An update with an explicitly bumped `updated_at` (role/active edits) still stores exactly that value.

## Gherkin Scenarios

```gherkin
Feature: Saving a user's new password

  Scenario: A password-only update is saved and returned on Postgres
    Given a user stored in Postgres
    When only the user's hashed password changes and the repository updates the user
    Then the returned user carries the new hash and the database-set updated_at
    And reloading the user shows the same hash and updated_at

  Scenario: An update keeps an explicitly bumped updated_at
    Given a user stored in Postgres
    When the user's role changes with an explicit updated_at and the repository updates the user
    Then the stored user has the new role and exactly that updated_at
```

Plus `admin.feature` "Admin resets user password" and `auth.feature` "Change own password" (now referenced by
tests; their pinned-500 twins are removed).

## Delta

### ADDED

- `backend/tests/features/user_password_update.feature`, `backend/tests/integration/test_user_repository_update_pg.py`.

### MODIFIED

- `PostgresUserRepository.update` refreshes before `to_entity()`.
- Identity safety-net tests assert 204/200 + log-in checks; the fixture resets the login rate limiter per test.

### REMOVED

- The two "currently 500s" scenarios and their baseline entries.

## Affected Areas

- Backend: identity repository.
- Frontend: none.
- Database: none (no schema change).
- API: change-password and admin reset-password stop returning 500.
- Tests: integration (SQLite app flow + Postgres repository).
- Docs: none.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: AE-0511 (self-service change-password UI).
- Blocked by: none.
- Related: AE-0097 (pinned the defect baseline).

## Implementation Plan

1. Flip the pinned-500 tests to the intended contract and add the Postgres repository test (red).
2. Refresh the model after the flush in `update` (green).
3. Replace the pinned scenarios, shrink the gherkin baseline.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-22 17:20

Reproduced: both endpoints 500 with `database_error` "greenlet_spawn has not been called"; the repository test fails
with `MissingGreenlet` on Postgres 16. Fixed with a refresh after the flush; all identity tests green.

## Files Touched

- backend/src/rag_backend/infrastructure/database/user_repository.py
- backend/tests/integration/test_user_repository_update_pg.py (new)
- backend/tests/integration/test_identity_conversation_safety_net.py
- backend/tests/features/user_password_update.feature (new), admin.feature, auth.feature
- scripts/gherkin_refs_baseline.json (shrink)

## Test Evidence

See `.agent/reports/AE-0490.dev-summary.md`.

## QA Report

`.agent/reports/AE-0490.qa.md`.

## Decision Log

- Refresh in the repository rather than bumping `updated_at` in each handler: every caller of `update` is fixed,
  and the database stays the source of the timestamp.

## Blockers

None.

## Final Summary

Pending.
