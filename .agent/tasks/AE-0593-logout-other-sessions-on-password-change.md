# AE-0593 — A password change logs out every other session

Status: In Development
Tier: T1
Priority: High
Type: Feature
Area: Backend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0593-logout-other-sessions
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-01

## Goal

When a user changes their password, every other session of that user is logged out; the session that made the
change stays signed in (Pedro's decision, 2026-11-01). Implemented with token versioning.

## Problem

AE-0511 lets a user change their own password, but an access token is a stateless JWT that is only checked for its
signature, type and expiry. A session somebody else opened with the old password (a shared or leaked password, a
forgotten browser) keeps working until its token expires, so changing the password does not lock anybody out.

## Scope

- `users.token_version INTEGER NOT NULL DEFAULT 0`: ORM model, entity mapping, Alembic revision `c0d1e2f3a4b5`
  (single head, after `b9c0d1e2f3a4`), idempotent prod one-shot
  `python -m rag_backend.scripts.token_version_column --apply --verify` in `deploy.yml` (after the
  `must_change_password` step, before `up -d`, with the in-stack retry and the end-of-job failure), so the drift
  check (`check_drift_cli`) sees the column.
- Access tokens carry `tv` = the user's `token_version` at issue time (`infrastructure/auth.py:create_access_token`).
- A token whose `tv` differs from the stored version answers 401 `Invalid or expired token` (with
  `WWW-Authenticate: Bearer`), exactly like an expired token. A token without `tv` counts as version 0 (no mass
  logout at deploy). A `tv` that is not a whole number is refused.
- The check runs in the three dependencies that load the user (one DB read per request, the read that already
  happened): `require_signed_in_user` (so also `require_authenticated_user`, `require_admin`,
  `require_editor_or_admin`, `/api/auth/me`, `/api/auth/change-password`), `get_optional_user` (a stale token is a
  visitor) and `api/dependencies/roles.get_current_user` (`CurrentUser`, `EditorUser`, `AdminUser`, `RoleUser`).
- `change_password` bumps `token_version` in the same Unit of Work write as the hash (entity `User.change_password`,
  used by both `AuthCommandHandler` and `UserService`). The handler returns a fresh token at the new version; the
  route sets it in the `access_token` cookie with the login's flags (HttpOnly, Secure on HTTPS, SameSite=Strict,
  Path=/, max age = token lifetime). Status stays 204.
- The repository never lowers the stored version (an update built from a user read before a change keeps the newer
  version).

## Non-Goals

- Admin password reset, logout endpoint changes, refresh tokens (out of scope by Pedro's decision, 2026-11-01).
- A response body for `change-password` (the browser holds the session in the cookie; the API contract stays 204).
- Frontend changes: the browser sends only the HttpOnly cookie (`authenticatedFetch` with `credentials: include`,
  server-side Next code forwards the incoming cookie), so the cookie the backend sets keeps the session; a stale
  session gets 401 and the existing api-client redirect to `/auth/logout` clears it.

## Acceptance Criteria

- [x] AC1 A new access token carries `tv` equal to the user's `token_version`.
- [x] AC2 A successful change stores the new hash, bumps `token_version` by one and clears `must_change_password`,
      committed once.
- [x] AC3 The changing session gets a fresh `access_token` cookie with the login's attributes and keeps working on
      me, a protected endpoint and an editor-only endpoint.
- [x] AC4 Every other session's token is refused with 401 on me, a protected endpoint and an editor-only endpoint;
      an endpoint open to visitors treats it as a visitor.
- [x] AC5 A token without `tv` works for a user at version 0 and is refused after the first change; a text `tv` is
      refused.
- [x] AC6 A wrong current password and a reused current password bump nothing, set no cookie and log nobody out.
- [x] AC7 Every HTTP and websocket route of the real app that reads the token goes through a version-checking
      dependency (inventory test, with a seeded-violation test that proves it fires).
- [x] AC8 The column one-shot adds `INTEGER NOT NULL DEFAULT 0` on an existing table, is idempotent, verify fails
      while missing, and it is a no-op without `users` or outside Postgres; the deploy runs it before the stack comes
      up, retries once in the running backend and fails the job at the end.
- [x] AC9 An update read before a change never lowers the stored version (Postgres).
- [x] AC10 The existing rules stay: reusing the current password is refused, `must_change_password` is cleared by a
      change, the change is rate limited.

## Gherkin Scenarios

- `backend/tests/features/logout_other_sessions_ae0593.feature`

## Delta

### ADDED

- `backend/src/rag_backend/api/dependencies/token_version.py` (claim read + 401).
- `backend/src/rag_backend/infrastructure/database/token_version_column.py`,
  `backend/src/rag_backend/scripts/token_version_column.py`.
- `backend/alembic/versions/c0d1e2f3a4b5_users_token_version.py`.
- Tests: `tests/unit/modules/identity/test_token_version_ae0593.py`,
  `tests/unit/api/test_token_version_inventory_ae0593.py`, `tests/unit/scripts/test_token_version_column_ae0593.py`,
  `tests/unit/scripts_ci/test_deploy_token_version_column_ae0593.py`,
  `tests/integration/test_logout_other_sessions_ae0593.py`,
  `tests/integration/test_logout_other_sessions_pg_ae0593.py`,
  `tests/integration/test_token_version_column_pg_ae0593.py`.

### MODIFIED

- `User` entity (`token_version`, bumped by `change_password`), `UserModel`, `PostgresUserRepository.update`.
- `create_access_token` (`tv` claim); `require_signed_in_user`, `get_optional_user`, `roles.get_current_user`.
- `AuthCommandHandler.change_password` returns the fresh token; `POST /api/auth/change-password` sets the cookie
  (login and change share one cookie helper).
- `.github/workflows/deploy.yml` (one-shot, retry, final check); `docs/architecture/openapi.json` (route docstring).
- `tests/integration/test_autopilot_migration.py` (single head), `tests/unit/api/test_roles.py` (doubles carry
  `token_version`), AE-0511 flow tests: after a change they continue with the session cookie like the browser does
  (`change_password_support.sign_in`), because the old bearer token is now logged out by design.

### REMOVED

- None.

## Affected Areas

- Backend: identity (entity, handler, route), auth dependencies, JWT helper, users table.
- Database: additive column `users.token_version` (Alembic + prod one-shot).
- API: `POST /api/auth/change-password` now also sets `access_token` (still 204); stale tokens answer 401.
- Deploy: one more idempotent one-shot before `up -d`.

## Dependencies

- Blocked by: AE-0511 (self-service change), AE-0587.
- Related: AE-0511, AE-0587, AE-0578 (schema drift check).

## Implementation Plan

1. Gherkin.
2. Column (model, entity, migration, one-shot, deploy), `tv` claim, version check in the user-loading dependencies.
3. Change bumps the version; route sets the fresh cookie.
4. Unit, inventory, SQLite flow and Postgres tests; adapt the AE-0511 flows to the cookie session.
5. Gates per backend gate, then `gate-capture.sh backend`; Python 3.11 import check.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-01

Ticket created from Pedro's decision (2026-11-01). Token paths inventoried: `decode_access_token` is called only by
`api/middleware/auth.py` (`get_current_user`, `get_current_user_optional`) and by the identity
`JwtTokenIssuer.decode_access_token` behind `AuthenticationService.validate_token`, which has no production caller
(tests only). The raw payload reaches routes only through `require_signed_in_user`, `get_optional_user` and
`roles.get_current_user`, the three dependencies that already load the user; there is no websocket route in the
app (the `/ws` rewrite in Next has no backend handler) and the SSE routes use the same dependencies. The
version check sits in those three, so it costs no extra DB read.

## Files Touched

See Delta.

## Test Evidence

Pending (dev summary).

## QA Report

Pending.

## Decision Log

- Pedro's decision (2026-11-01): a password change logs out every other session of the user; the changing session
  stays signed in; token versioning.
- A token without `tv` counts as version 0, so the deploy logs nobody out.
- A stale token on an endpoint open to visitors is a visitor (like an expired one), not a 401.
- The stale check runs before the forced-change check: a stale token is not signed in at all.
- `change-password` stays 204 and sets the cookie; no body. A bearer-only API client must log in again after a
  change.
- The repository writes `max(stored, entity)` for the version so an update read before a change cannot revive the
  logged-out tokens.

## Blockers

None.

## Final Summary

Pending.
