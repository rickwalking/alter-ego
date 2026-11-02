# AE-0595 — An admin password reset logs out the user's open sessions

Status: In Development
Tier: T1
Priority: High
Type: Feature
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0595-admin-reset-logout
Kanban Card: TBD
Created: 2026-11-02
Updated: 2026-11-02

## Goal

When an admin resets a user's password, every open session of that user is logged out, following Pedro's earlier
choice that a password change ends other sessions (Pedro's decision, 2026-11-02). Reuses the AE-0593 token version.

## Problem

AE-0593 bumps `users.token_version` on a self-service password change, so older access tokens get 401. The admin
reset (`AdminUserHandler.reset_password`, `User.reset_password`) stores a new temporary hash and sets
`must_change_password`, but leaves the version alone. A session opened before the reset (for example by whoever
learned the old password) survives it: it gets 403 `password_change_required` on most routes, but still reaches
`/api/auth/me` and `/api/auth/change-password`.

## Scope

- `User.reset_password` bumps `token_version` by one, in the same Unit of Work write as the temporary hash and
  the `must_change_password` flag.
- `AdminUserHandler.reset_password` reads the user with `UserRepository.get_by_id_for_update`
  (`SELECT ... FOR UPDATE`, re-read past the identity map), inside the Unit of Work, so the row stays locked until
  the commit. A reset racing a self-service change (which takes the same lock) runs after it, or before it, and
  each bumps from the committed version.
- The admin's own session is not touched when they reset somebody else (only the target row changes).
- The endpoint has no self guard: an admin may reset their own password through it. In that case their current
  token is stale too (401 on the next request) and they sign in with the temporary password. No special case.
- No schema change, no new column, no API contract change (`POST /api/admin/users/{id}/reset-password` still
  answers 200 with `temp_password`).

## Non-Goals

- The stale write in `PostgresUserRepository.update` (writes every field from a possibly stale entity), that is
  AE-0596.
- Frontend changes: a logged-out session gets 401 and the existing api-client redirect to `/auth/logout` clears it.
- Refresh tokens, a logout endpoint change.

## Acceptance Criteria

- [x] AC1 An admin reset stores the temporary hash, sets `must_change_password` and bumps `token_version` by one,
      committed once, from the user row read locked.
- [x] AC2 After a reset, a session of the user opened before it gets 401 `Invalid or expired token` on `/me`,
      `change-password` and a protected endpoint.
- [x] AC3 The temporary password signs in; `/me` reports `must_change_password`, a protected endpoint answers 403
      `password_change_required`, and the change from the temporary password succeeds.
- [x] AC4 The resetting admin's session keeps working on `/me` and the admin users list, and their version is
      unchanged.
- [x] AC5 An admin who resets their own password through the endpoint is logged out (401 on `/me`) and signs in
      again with the temporary password.
- [x] AC6 A failed reset (unknown user: 404; caller is not an admin: 403) changes no token version and commits
      nothing.
- [x] AC7 On Postgres, a reset waits for a concurrent holder of the user row lock and bumps from its committed
      version (the version ends two higher).

## Gherkin Scenarios

- `backend/tests/features/admin_reset_logs_out_ae0595.feature`

## Delta

### ADDED

- `backend/tests/features/admin_reset_logs_out_ae0595.feature`.
- Tests: `tests/unit/modules/identity/test_admin_reset_logout_ae0595.py`,
  `tests/integration/test_admin_reset_logout_ae0595.py` (SQLite flow),
  `tests/integration/test_admin_reset_logout_pg_ae0595.py` (Postgres flow and row lock).

### MODIFIED

- `backend/src/rag_backend/domain/models/user.py` (`User.reset_password` bumps `token_version`).
- `backend/src/rag_backend/modules/identity/application/admin_handlers.py` (`reset_password` reads the user locked).

### REMOVED

- None.

## Affected Areas

- Backend: identity entity and admin handler.
- API: no contract change; sessions of a reset user now answer 401.

## Dependencies

- Blocked by: AE-0593 (token version).
- Related: AE-0511, AE-0587, AE-0596 (stale write in the user repository update).

## Implementation Plan

1. Gherkin.
2. Bump in `User.reset_password`; locked read in the admin reset.
3. Unit, SQLite flow and Postgres tests, each proven to fail without the bump (and the lock tests without the lock).
4. Gates per backend gate (no local mutation), then `gate-capture.sh backend`; Python 3.11 import check.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-02

Ticket created from Pedro's decision (2026-11-02). Implemented the bump and the locked read. The new tests were run
with the bump removed (7 fail) and with the plain `get_by_id` read restored (3 fail: the locked-read unit checks and
the Postgres lock test), then green with the change.

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0595.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- Pedro's decision (2026-11-02): an admin reset also logs out the user's open sessions.
- The bump lives in the entity (`User.reset_password`), like the change's, so every caller of the reset gets it.
- The reset takes the same row lock as the change; no SQL increment.
- An admin resetting their own password through the admin endpoint is logged out like any other user: the endpoint
  allows it today and no special case is added.

## Blockers

None.

## Final Summary

Pending.
