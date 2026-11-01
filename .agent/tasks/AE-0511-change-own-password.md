# AE-0511 — Change my own password, and change a reset password at the next sign-in

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Full-stack
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/ae-0511-change-own-password
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-11-01

## Goal

Any signed-in user changes their own password from the dashboard, and a user whose password an admin reset must
change the temporary password before using the app (Pedro's decision, 2026-10-31).

## Problem

`POST /api/auth/change-password` works since AE-0490, but nothing in the dashboard calls it: users cannot change
their password themselves. "Redefinir senha" on /admin/users gives the admin a temporary password, and the user can
keep using it forever, so the admin keeps knowing a working password of another account. AE-0490 left both as
follow-ups (its Non-Goals point here).

## Scope

- Backend: one additive column `users.must_change_password` (`BOOLEAN NOT NULL DEFAULT false`). An admin reset sets
  it; a successful self change clears it; a normal self change never sets it.
- Backend: every protected endpoint except `/api/auth/me`, `/api/auth/change-password` and `/api/auth/logout`
  answers 403 `{"detail": "Password change required", "code": "password_change_required"}` while the flag is set
  (`require_authenticated_user` and the `roles` dependencies). Endpoints with an optional user treat a flagged user
  as an anonymous visitor.
- Backend: `/api/auth/me` exposes `must_change_password`. change-password keeps the password rules and bcrypt hashing,
  answers a wrong current password with 401 `current_password_incorrect`, a new password equal to the current one with
  400 `password_unchanged`, and is rate limited like the login (5/minute). Nothing changes on any error.
- Schema delivery: an Alembic revision plus the idempotent one-shot
  `python -m rag_backend.scripts.must_change_password_column --apply --verify`, run by `deploy.yml` before the stack
  comes up (AE-0578 pattern; the post-stack-up drift check already exists).
- Frontend: a change-password page (`/dashboard/account/password`, pt/en) linked from the sidebar footer; the app
  shell keeps a flagged user on that page; an API 403 `password_change_required` sends the browser there; the reset
  dialog shows the temporary password once with a note that the user must change it at the next sign-in.

## Non-Goals

- Email reset links / "forgot password".
- Flagging users an admin creates with a generated password (only resets, per Pedro's decision).
- Ending other sessions when a password changes; a JWT claim for the flag (the API reads the column on each request).
- Any other DDL, data rewrite or drop.

## Acceptance Criteria

- [x] AC1 A signed-in user changes their password with the current one: 204, the new password logs in, the old one
      does not, the flag stays false.
- [x] AC2 A wrong current password answers 401 `current_password_incorrect` and changes nothing; a new password equal
      to the current one answers 400 `password_unchanged`; a too-short one 422; more than 5 tries a minute 429.
- [x] AC3 An admin reset returns the temporary password once and sets `must_change_password`.
- [x] AC4 With the flag set, the user can log in, `/me` reports `must_change_password: true`, logout works, and every
      other protected endpoint answers 403 `password_change_required` (also the role-guarded ones).
- [x] AC5 Changing the temporary password clears the flag and the protected endpoints answer normally.
- [x] AC6 A Postgres integration test covers reset → temp login → 403 code → change → flag cleared → 200, and the
      wrong-current-password case.
- [x] AC7 The one-shot adds the column idempotently (`--apply --verify` exit 0, second run adds nothing, `--verify`
      alone exits 1 while missing, no table / not Postgres is a no-op, no mode is a usage error), and the deploy runs
      it before stack up with the failure captured and the job failing at the end.
- [x] AC8 The dashboard has a pt/en change-password page with the forced-change notice, redirects a flagged user there
      from any other dashboard/admin page, and the reset dialog notes the password is shown once and must be changed.

## Gherkin Scenarios

- `backend/tests/features/change_own_password_ae0511.feature`
- `frontend/tests/features/change-own-password-ae0511.feature`

## Delta

### ADDED

- Column `users.must_change_password`, Alembic revision `b9c0d1e2f3a4`, one-shot `must_change_password_column`.
- `/dashboard/account/password` page, `PasswordChangeGate`, sidebar footer link.
- Error codes `password_change_required`, `current_password_incorrect`, `password_unchanged`.

### MODIFIED

- `/api/auth/me` (adds `must_change_password`), `/api/auth/change-password` (coded errors, unchanged-password check,
  rate limit), admin reset (sets the flag), auth dependencies (403 while flagged).
- Reset dialog copy (pt/en).

### REMOVED

- None.

## Affected Areas

- Backend: identity module, auth dependencies, auth routes, users ORM model.
- Frontend: identity module, app shell, api-client, admin reset dialog, sidebar footer, i18n.
- Database: one additive column (Alembic + deploy one-shot).
- API: `/api/auth/me`, `/api/auth/change-password`, 403 `password_change_required` on protected endpoints.
- Tests: unit, SQLite app flow, Postgres integration, deploy ordering, vitest.
- Docs: `docs/architecture/openapi.json`.
- Deployment: `.github/workflows/deploy.yml` one-shot step.

## Dependencies

- Blocked by: AE-0490 (change-password and reset no longer 500).
- Related: AE-0578 (one-shot + drift check pattern), AE-0514 (reset dialog).

## Implementation Plan

1. Gherkin (backend + frontend).
2. Column, entity methods, handlers, dependencies, routes; Alembic revision and one-shot; deploy step.
3. Tests (unit, SQLite flow, Postgres flow, one-shot, deploy ordering); OpenAPI artifact.
4. Frontend page, gate, api-client redirect, sidebar link, reset note, i18n; vitest.
5. Full gates per scope.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-31

Ticket created from Pedro's decision (2026-10-31). The schema stays within the one additive column he allowed:
`ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false` (constant default,
no table rewrite on Postgres 11+).

Developer: backend and frontend implemented Gherkin first. Enforcement lives in the user-resolving dependencies:
`require_signed_in_user` (no flag check, used only by `/me` and change-password) under `require_authenticated_user`
(403 while flagged), the same check in `roles.get_current_user`, and `get_optional_user` returns None for a flagged
user. The temporary password was already shown only in the reset dialog; the dialog now also says it must be changed.
Added (not in the decision, flagged for review): change-password refuses a new password equal to the current one, so a
temporary password cannot be "changed" to itself.

### 2026-11-01

Full backend run 1: 15 alembic chain tests failed (the shared `ALEMBIC_HEAD` constant still named the boost revision,
and the new revision read `users` columns on partial schemas some tests stamp). Bumped the constant with a chain check,
and the revision now leaves a database without `users` alone. Run 2: only the AE-0583 flake; run 3 green. Frontend
scope green.

Review (no blockers), two fixes: `deploy.yml` retries a failed column one-shot once in the running backend
(`exec -T backend ... --apply --verify`) before the drift check, so a missed column does not leave every sign-in at
500 (a successful retry clears `MUST_CHANGE_PASSWORD_EXIT`; a second failure still fails the job at the end); and
`tests/unit/api/test_password_change_gate_inventory_ae0511.py` walks every HTTP and websocket route of `create_app()`
and asserts only `/api/auth/me` and `/api/auth/change-password` reach the raw token without the flag check, with a
seeded app proving it fires (raw parameter, route-level dependency, websocket). Full backend scope re-run green.

## Files Touched

- `backend/src/rag_backend/domain/models/user.py`, `infrastructure/database/models/user.py`,
  `infrastructure/database/user_repository.py`
- `backend/src/rag_backend/modules/identity/{constants,public,__init__}.py`, `application/{__init__,admin_handlers,auth_handlers,user_service}.py`
- `backend/src/rag_backend/api/constants.py`, `api/dependencies/{auth,roles}.py`, `api/routes/auth.py`
- `backend/alembic/versions/b9c0d1e2f3a4_users_must_change_password.py` (new)
- `backend/src/rag_backend/infrastructure/database/must_change_password_column.py`,
  `backend/src/rag_backend/scripts/must_change_password_column.py` (new)
- `.github/workflows/deploy.yml` (one-shot step + in-stack retry), `docs/architecture/openapi.json`
- `backend/tests/unit/api/test_password_change_gate_inventory_ae0511.py` (new)
- `backend/tests/features/change_own_password_ae0511.feature` (new)
- `backend/tests/integration/change_password_support.py`, `test_change_own_password_ae0511.py`,
  `test_change_own_password_pg_ae0511.py`, `test_must_change_password_column_pg_ae0511.py` (new)
- `backend/tests/unit/modules/identity/test_forced_password_change_ae0511.py`,
  `tests/unit/scripts/test_must_change_password_column_ae0511.py`,
  `tests/unit/scripts_ci/test_deploy_must_change_password_column_ae0511.py` (new)
- `backend/tests/unit/api/test_roles.py`, `backend/tests/snapshots/identity/auth_me.json`,
  `backend/tests/integration/test_autopilot_migration.py` (single-head constant)
- `frontend/src/app/dashboard/account/password/{page,layout}.tsx`, `change-password-page.test.tsx` (new)
- `frontend/src/components/account/change-password-form.tsx`, `components/layout/password-change-gate.tsx` (+ test) (new)
- `frontend/src/modules/identity/{index,types}.ts`, `lib/change-password.ts` (+ test), `hooks/use-change-password.ts`
- `frontend/src/lib/api-client.ts` (+ test), `lib/page-metadata.ts`, `constants/{auth,dashboard-routes}.ts`,
  `schemas/identity.ts`
- `frontend/src/components/layout/neon-app-shell.tsx`, `components/organisms/neon-sidebar-user-footer.tsx`,
  `sidebar-change-password-link.test.tsx` (new), `components/admin/change-password-dialog.tsx`,
  `reset-password-once.test.tsx` (new)
- `frontend/src/i18n/locales/{en,pt}.json`, `frontend/scripts/url-inventory.snapshot.json`,
  `frontend/tests/features/change-own-password-ae0511.feature` (new)
- Test mocks for the shell gate: `src/app/shell-skip-link.test.tsx`, `src/app/dashboard/{dashboard-menu-button,layout-menu-button}.test.tsx`,
  `src/app/(admin)/admin/admin-shell.test.tsx`, `src/app/page-titles.test.ts`

## Test Evidence

Full gate runs at fb06daaa1 (`gate-capture.sh`, one scope at a time). Backend, Postgres-backed: 8085 passed, 2
skipped; the new Postgres flow and one-shot tests PASSED (not skipped). The first backend run failed 15 alembic chain
tests (the shared single-head constant and a revision that assumed a `users` table); fixed in fb06daaa1. The second
hit only the known AE-0583 aiosqlite unclosed-connection flake (`test_publishing_safety_net.py`); the third was green.

Backend, rerun at f12839c6f after the review fixes (8089 passed, 2 skipped; Postgres tests PASSED):

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

Backend, earlier run at fb06daaa1:

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

Frontend (427 files, all passed):

GATES_JSON: {"pass":18,"fail":0,"skip":1,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:blog-v1-dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:gherkin-refs","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"SKIP"}]}

Mutation runs in CI only (AE-0448).

## QA Report

Pending.

## Decision Log

- Pedro's decision (2026-10-31): self-service change for every signed-in user; an admin reset forces a change at the
  next sign-in, enforced by the API; one additive column only.
- The flag is read from the database on every request (the user is already loaded per request), not put in the JWT:
  a reset takes effect on sessions that were open before it, and the JWT payload stays unchanged.
- A flagged user is anonymous on optional-user endpoints instead of 403, so public pages keep working.

## Blockers

None.

## Final Summary

Pending.
