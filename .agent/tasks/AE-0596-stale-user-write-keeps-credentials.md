# AE-0596 — A stale user write must never restore an old password hash or token version

Status: In Progress
Tier: T1
Priority: High
Type: Bugfix
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0596-stale-user-write
Kanban Card: TBD
Created: 2026-11-02
Updated: 2026-11-02

## Goal

No user write can put back an old password hash or an old token version. Pedro's decision (2026-11-02): this is a
security bug, fix it.

## Problem

`AdminUserHandler.update` and `PostgresUserRepository.update` write every column from an entity that may have been
read earlier, without a lock. If a password change or an admin reset (both bump `users.token_version`, AE-0593 /
AE-0595) commits in between, the stale write restores the old `hashed_password` and the old `token_version`: the
revoked password works again and the logged-out sessions come back.

## Scope

- `User` records which of its persisted fields were assigned after it was built (`User.changed_fields()`), whether
  through a mutator or a direct assignment. `PostgresUserRepository.update` writes only those columns, so a
  profile or role edit never writes `hashed_password` or `token_version`.
- Every user update path reads the user with `get_by_id_for_update` (`SELECT ... FOR UPDATE`, re-read past the
  identity map) inside the Unit of Work, so the row stays locked until the commit:
  `AdminUserHandler.update` / `reset_password`, `UserService.update` / `assign_role`,
  `AuthCommandHandler.change_password`.
- Lock order in `AdminUserHandler.update`: when the edit touches role or active state, the active-admin rows are
  locked (the AE-0585 count) before the user row, then the last-admin guard runs on the fresh locked user. Every
  writer takes at most "active-admin rows, then one user row", so two admin edits never deadlock.
- The active-admin lock query orders by id, so two transactions lock the same rows in the same order.
- No schema change, no API contract change.

## Non-Goals

- Optimistic version columns or SQL-level `token_version = token_version + 1` (the row lock is enough).
- A last-admin guard in `UserService.assign_role` (no route uses it; unchanged behaviour).
- Frontend changes.

## Acceptance Criteria

- [ ] AC1 `User.changed_fields()` is empty for a freshly built or loaded entity and holds exactly the persisted
      fields assigned since (mutator or direct assignment); `id` and `created_at` are never tracked.
- [ ] AC2 `PostgresUserRepository.update` writes only the changed fields: an entity read before a password change
      and renamed after it commits keeps the new hash and the bumped token version.
- [ ] AC3 `AdminUserHandler.update`, `UserService.update`, `UserService.assign_role` and
      `AuthCommandHandler.change_password` read the user locked inside the Unit of Work (a refused change rolls
      back, commits nothing).
- [ ] AC4 On Postgres, an admin profile edit racing a password change (two sessions, real row lock) waits for the
      lock, and afterwards the new hash, the bumped token version and the new name are all stored.
- [ ] AC5 The AE-0585 mutual deactivation on Postgres still leaves one active admin, and two admin edits queued
      behind a password change on one admin's row never deadlock.
- [ ] AC6 Existing contracts unchanged: 404 before 422 on an admin edit of a missing user with a bad role, the
      last-active-admin guard, the reset and the change flows.

## Gherkin Scenarios

- `backend/tests/features/stale_user_write_ae0596.feature`
- The mutual deactivation of AC5 stays in `backend/tests/features/last_active_admin_guard_ae0585.feature`
  (`tests/integration/test_last_active_admin_lock_pg_ae0585.py`), re-run green on Postgres.

## Delta

### ADDED

- `backend/tests/features/stale_user_write_ae0596.feature`.
- Tests: `tests/unit/modules/identity/test_stale_user_write_ae0596.py`,
  `tests/unit/infrastructure/test_user_repository_changed_fields_ae0596.py`,
  `tests/integration/test_stale_user_write_pg_ae0596.py`.

### MODIFIED

- `backend/src/rag_backend/domain/models/user.py` (field tracking, `UserField`, `change_email`).
- `backend/src/rag_backend/infrastructure/database/user_repository.py` (changed-fields-only write; ordered lock).
- `backend/src/rag_backend/modules/identity/application/admin_handlers.py` (locked read, lock order).
- `backend/src/rag_backend/modules/identity/application/user_service.py` (locked read, mutators).
- `backend/src/rag_backend/modules/identity/application/auth_handlers.py` (locked read inside the UoW).
- Test doubles: the identity service fake repository gains `get_by_id_for_update`.

### REMOVED

- None.

## Writers of the users table (audit)

| Writer | What it writes | Done |
|--------|----------------|------|
| `AdminUserHandler.update` (`PATCH /api/admin/users/{id}`) | name / role / active | locked read in the UoW (after the active-admin lock); changed fields only |
| `AdminUserHandler.reset_password` | hash, flag, version | already locked (AE-0595); changed fields only |
| `AuthCommandHandler.change_password` | hash, flag, version | locked read moved inside the UoW; changed fields only |
| `UserService.update` / `assign_role` (facade, no route) | name / email / active / role | locked read in the UoW; mutators; changed fields only |
| `PostgresUserRepository.update` | the columns above | writes only `User.changed_fields()` |
| `PostgresUserRepository.create`, `scripts/bootstrap_admin.py`, `UserService.create`, `AdminUserHandler.create` | new row (INSERT) | no change: an insert has no stale row to overwrite |
| `scripts/seed_production.py` | `INSERT ... ON CONFLICT DO NOTHING` | no change: never updates an existing row |
| `PostgresUserRepository.delete`, `AdminUserHandler.delete` | DELETE | no change: no column written |
| `cover_generations.py`, `count_active_by_role` | `SELECT ... FOR UPDATE` only | no write; the count now orders by id |
| `scripts/seed_e2e_carousel_fixtures.py`, auth dependencies | reads only | no change |

## Affected Areas

- Backend: identity entity, user repository, identity handlers.
- API: no contract change.

## Dependencies

- Stacked on AE-0595 (PR #336); merges after it.
- Related: AE-0585 (active-admin lock), AE-0593, AE-0595.

## Implementation Plan

1. Gherkin.
2. Field tracking in `User`; changed-fields-only repository write.
3. Locked reads in every update path; lock order in the admin edit.
4. Unit and Postgres tests, each proven to fail without the fix.
5. Every backend gate (no local mutation), then `gate-capture.sh backend`; Python 3.11 import check.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-02

Ticket created from Pedro's decision (2026-11-02). Audit of the users-table writers recorded above.

Implemented the field tracking, the changed-fields-only write and the locked reads. Proof that the tests bite:

- Repository writing every field again: the SQLite stale-rename and no-change tests and the Postgres stale-copy
  test fail (3 fail).
- Handlers back on plain `get_by_id`: 8 unit tests fail (every locked-read check).
- Admin edit locking the user row before the admin count: the unit order test fails (2 cases), and the Postgres
  "edits queued behind a password change" test deadlocks (`DeadlockDetectedError`) in 2 of 3 runs (whether it
  deadlocks depends on how the two random ids sort); with the new order it passed 3 of 3.

Finding: the Postgres race test (admin rename waiting on a password change) also passes on the original code.
SQLAlchemy only sends the columns that differ from the session's own loaded copy of the row, and in that path the
entity and the session copy are the same stale snapshot, so the UPDATE only carries the name. The stale write
restores a hash or version when the entity differs from the session's copy: an entity kept across a commit
(`expire_on_commit` reloads the row), carried from another session, or read before a `populate_existing` re-read.
The stale-copy tests (SQLite and Postgres) reproduce that and fail on the old code. The race test stays as the
proof of AC4 (the edit waits on the lock and the credentials survive).

## Files Touched

See Delta.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Changed fields are tracked by the entity (`__setattr__` after construction), not passed by each caller: a
  direct assignment (as `UserService` did) can never be silently dropped, and no caller can forget a field.
- Writing only changed fields plus the row lock, not a version column: no schema change, and the lock already
  exists since AE-0593.
- In the admin edit the active-admin rows are locked before the user row. Locking the user row first would let
  two admins deactivating each other deadlock (each holds its target and waits on the other's in the count).
- The admin edit keeps a plain read first, so a missing user still answers 404 before a bad role answers 422.
- `change_password` now reads inside the UoW: a refused change rolls back and releases the lock at once.
- The `UserField` members for the credential columns are named `CREDENTIAL_HASH`, `CREDENTIAL_CHANGE_REQUIRED`
  and `SESSION_VERSION` (values are the real column names), so bandit S105 does not flag them and no `noqa` is
  needed.
- `UserService.update` now goes through the entity mutators (`rename`, `change_email`, `activate`/`deactivate`),
  which also refresh `updated_at`; the column's `onupdate` already set it on every UPDATE, so the stored result is
  the same.

## Blockers

None.

## Final Summary

Pending.
