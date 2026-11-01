# AE-0585 — The last active admin can be deactivated

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Full-stack
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0585-last-admin-guard
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

An admin can never leave the app without an active admin: deactivating or demoting the last active admin is refused.

## Problem

Found in the AE-0528 review (2026-10-31). The admin update use case guards a role change of the last admin
(`_apply_role` raises `LastAdminError`, HTTP 409), but `_apply_active`
(`backend/src/rag_backend/modules/identity/application/admin_handlers.py`) lets the last active admin be deactivated.
If the only admin deactivates their own account (or another admin deactivates the last active one), nobody can sign
in to the admin area any more.

## Scope

- Backend: refuse to deactivate the last active admin, and refuse to demote the last ACTIVE admin (a demotion check
  that only counts admins, active or not, must count active admins), with the same 409 and a clear error code.
- Frontend: the users table / edit dialog shows a pt/en message for that 409, and disables the deactivate/demote
  control for the last active admin with an explanation.
- Tests: unit tests for the guard, and a Postgres integration test of the API (deactivate last active admin → 409,
  nothing changed; with two active admins → allowed; demote last active admin while another admin is inactive → 409).

## Non-Goals

- Delete-user rules (already guarded), roles beyond admin/editor, any schema change.

## Acceptance Criteria

- [x] AC1 Deactivating the last active admin returns 409 with a clear error code and leaves the user active.
- [x] AC2 Demoting the last active admin returns 409, also when other admins exist but are inactive.
- [x] AC3 With two active admins, deactivating or demoting one is allowed.
- [x] AC4 The UI shows the pt/en message and disables the control for the last active admin.
- [x] AC5 A Postgres integration test covers AC1-AC3.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

After AE-0514 (same admin dialog files) and AE-0528 (#322).

## Progress Log

### 2026-10-31

Ticket filed from the AE-0528 review. No product decision needed (safety rule).

Developer: Gherkin first (backend `last_active_admin_guard_ae0585.feature`, frontend
`last-active-admin-guard-ae0585.feature`). `AdminUserHandler.update` runs one guard before any mutation and counts
ACTIVE admins through the new `UserRepository.count_active_by_role`; a demotion raises `LastAdminError`, a deactivation
the new `LastActiveAdminDeactivationError` subclass, both 409 `last_admin` (the AE-0514 code, reused). Demoting an
inactive admin is now allowed. The users page finds the only active admin in the full list and the edit dialog locks
its role select and Active checkbox with a pt/en explanation. Full `gate-capture.sh all` run: only `backend:comments`
failed (multi-line Scenario comments, a ticket id in a docstring); fixed, then the full backend scope re-ran green.

Review round 1: concurrency fix — the active-admin count now selects the active admin ids `FOR UPDATE` and counts them
in Python (Postgres refuses `FOR UPDATE` on `count(*)`). Chosen over `pg_advisory_xact_lock` because it locks only the
rows the guard reads and needs no lock key; concurrent mutual deactivation is serialized and the second update is
refused. Added a deterministic Postgres blocking test, a mutual-deactivation Postgres test, a unit test that the
statement carries `FOR UPDATE`, and the Postgres case for deactivating while the other admin is inactive. The UI
helper now documents that its lock is only a hint. Full backend and frontend scopes re-ran green.

## Files Touched

- `backend/src/rag_backend/modules/identity/application/admin_handlers.py` — guard, `_AdminChange`, new error
- `backend/src/rag_backend/modules/identity/{constants,public,__init__}.py` — message + exports
- `backend/src/rag_backend/domain/protocols/repositories.py`, `infrastructure/database/user_repository.py` —
  `count_active_by_role`
- `backend/src/rag_backend/api/routes/admin.py`, `api/constants.py` — 409 mapping and details
- `backend/tests/features/last_active_admin_guard_ae0585.feature`
- `backend/tests/unit/modules/identity/test_last_active_admin_guard_ae0585.py` (new),
  `test_identity_handlers.py`, `test_identity_services.py`, `tests/unit/infrastructure/test_user_repository_contract.py`
- `backend/tests/integration/test_last_active_admin_guard_pg_ae0585.py`, `test_last_active_admin_lock_pg_ae0585.py`
  (new, Postgres); `backend/tests/unit/infrastructure/test_user_repository_lock_ae0585.py` (new)
- `docs/architecture/openapi.json` (409 description)
- `frontend/src/lib/last-active-admin.ts` (+ test), `frontend/src/constants/admin-users.ts`
- `frontend/src/components/admin/edit-user-dialog.tsx`, `user-active-field.tsx` (new), `user-dialog-parts.tsx`,
  `user-table.tsx`, `last-active-admin-lock.test.tsx` (new)
- `frontend/src/app/(admin)/admin/users/page.tsx`, `last-active-admin-page.test.tsx` (new)
- `frontend/src/i18n/locales/{en,pt}.json` (`admin.lastActiveAdminLocked`)
- `frontend/tests/features/last-active-admin-guard-ae0585.feature`

## Test Evidence

Full backend scope (`gate-capture.sh backend`, Postgres-backed, 8051 passed, 2 skipped; the new Postgres tests
PASSED, not skipped):

GATES_JSON: {"pass":26,"fail":0,"skip":1,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:gherkin-refs","status":"PASS"},{"gate":"backend:comments","status":"PASS"},{"gate":"backend:blog-v1-dead-code","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:openapi-fresh","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:duplication","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"SKIP"}]}

Full frontend scope (`gate-capture.sh frontend`):

GATES_JSON: {"pass":18,"fail":0,"skip":1,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:blog-v1-dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:gherkin-refs","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"SKIP"}]}

## QA Report

Pending.

## Blockers

None.
