# AE-0587 — Users an admin creates must change the password at the first sign-in

Status: Dev Complete
Tier: T1
Priority: High
Type: Feature
Area: Full-stack
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0587-force-change-for-created-users
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-01

## Goal

A user an admin creates must change the password at the first sign-in, the same way as after an admin reset
(Pedro's decision, 2026-11-01).

## Problem

AE-0511 added `users.must_change_password` and sets it only on an admin reset. "Criar usuário" on /admin/users
also hands the admin a working password of the new account (generated and shown once, or typed by the admin),
and the new user can keep it forever, so the admin keeps knowing it. AE-0511 left this out on purpose (its
Non-Goals).

## Scope

- Backend: `AdminUserHandler.create` stores the new user with `must_change_password = true`, for a generated
  password and for one the admin typed. The existing AE-0511 enforcement (403 `password_change_required` on every
  protected endpoint except `/api/auth/me`, `/api/auth/change-password`, logout) and clearing (a successful change)
  apply unchanged.
- Backend: the create route docstring (and so `docs/architecture/openapi.json`) says the new user must change the
  password at the first sign-in. The response shape is unchanged.
- Frontend: the create-user dialog says, before creating, that the new user must change the password at the first
  sign-in, and repeats it in the result (with the generated password, or with the plain success message when the
  admin typed one). pt/en.

## Non-Goals

- Any schema change (the AE-0511 column is reused).
- Flagging users created outside the admin create flow: the bootstrap owner script
  (`scripts/bootstrap_admin.py`), `UserService.create` (no HTTP route uses it), test fixtures. There is no public
  sign-up.
- Existing users created before this change are not flagged retroactively (no data rewrite).

## Acceptance Criteria

- [x] AC1 An admin create without a password returns the temporary password once and the stored user has
      `must_change_password = true`.
- [x] AC2 An admin create with a typed password returns no temporary password and the stored user is flagged too.
- [x] AC3 A refused create (duplicate email, invalid role) writes nothing.
- [x] AC4 The bootstrap owner script and `UserService.create` store the user unflagged.
- [x] AC5 A Postgres integration test covers admin create → login with the generated password → `/me` reports the
      flag → protected endpoint 403 `password_change_required` → change → 200, the generated password no longer
      logs in, the new one does.
- [x] AC6 The create-user dialog says the new user must change the password at the first sign-in, before and after
      creating, in pt and en, and never echoes a typed password.

## Gherkin Scenarios

- `backend/tests/features/force_change_for_created_users_ae0587.feature`
- `frontend/tests/features/create-user-must-change-ae0587.feature`

## Delta

### ADDED

- Feature files above; `backend/tests/unit/modules/identity/test_created_user_must_change_ae0587.py`,
  `frontend/src/components/admin/create-user-must-change.test.tsx`.
- i18n keys `admin.createUserDescription`, `admin.createMustChangeNote` (pt/en).

### MODIFIED

- `AdminUserHandler.create` sets the flag; create route docstring; OpenAPI artifact.
- Create-user dialog copy (form note + result note).
- `backend/tests/integration/test_change_own_password_pg_ae0511.py` (new create flow test),
  `change_password_support.py` (`create_by_admin`).

### REMOVED

- None.

## Affected Areas

- Backend: identity module admin handler, admin route docstring.
- Frontend: admin create-user dialog, i18n.
- Database: none (reuses `users.must_change_password`).
- API: `POST /api/admin/users` now flags the created user; response unchanged.
- Docs: `docs/architecture/openapi.json`.

## Dependencies

- Blocked by: AE-0511 (the flag, enforcement and change page).
- Related: AE-0511, AE-0491 (masked create-user password).

## Implementation Plan

1. Gherkin (backend + frontend).
2. Flag in `AdminUserHandler.create`; route docstring; OpenAPI artifact.
3. Unit tests (handler both password paths, refused create, service and bootstrap unflagged); Postgres flow.
4. Dialog notes + i18n; vitest.
5. Full gates per scope.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-01

Ticket created from Pedro's decision (2026-11-01). Create paths checked: `POST /api/admin/users`
(`AdminUserHandler.create`) is the only HTTP path that creates users; `UserService.create` has no route caller; the
bootstrap owner script prints its own one-time password to the operator; there is no sign-up route. Only the admin
create flow is flagged.

Developer: Gherkin first, then the one-line flag in `AdminUserHandler.create` (the User is built with
`must_change_password=True`), unit tests, the Postgres flow test, and the dialog notes. Focused backend (identity,
admin, auth, Postgres flow) and frontend admin/app suites green before the full runs. Full backend and frontend
scopes green on the first run.

## Files Touched

- `backend/src/rag_backend/modules/identity/application/admin_handlers.py`, `backend/src/rag_backend/api/routes/admin.py`
- `docs/architecture/openapi.json`
- `backend/tests/features/force_change_for_created_users_ae0587.feature` (new)
- `backend/tests/unit/modules/identity/test_created_user_must_change_ae0587.py` (new)
- `backend/tests/integration/change_password_support.py`, `backend/tests/integration/test_change_own_password_pg_ae0511.py`
- `frontend/src/components/admin/create-user-dialog.tsx`, `frontend/src/components/admin/create-user-must-change.test.tsx` (new)
- `frontend/src/i18n/locales/{en,pt}.json`, `frontend/tests/features/create-user-must-change-ae0587.feature` (new)

## Test Evidence

Full gate runs at ae980ffcf (`gate-capture.sh` via `laptop-gate heavy`, one scope at a time, `DATABASE_URL` on the
local Postgres). Backend: 8100 passed, 2 skipped; the new Postgres create flow test and the AE-0587 unit tests PASSED
(not skipped). No flake reruns needed.

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

Frontend:

GATES_JSON: {"pass":18,"fail":0,"skip":1,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:blog-v1-dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:gherkin-refs","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"SKIP"}]}

Mutation runs in CI only (AE-0448).

## QA Report

Pending.

## Decision Log

- Pedro's decision (2026-11-01): users an admin creates must change the password at the first sign-in.
- Every admin-created user is flagged, not only those with a generated password: the dialog lets the admin type the
  password (optional field), and a typed password is just as known to the admin as a generated one, so the
  consistent rule (same as a reset) is to flag every admin create.
- The bootstrap owner is not flagged: it is the first admin, created by the operator from the CLI, and it is not
  the admin create flow. It can still change its password from the dashboard.

## Blockers

None.

## Final Summary

Pending.
