# AE-0585 — The last active admin can be deactivated

Status: Intake
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

- [ ] AC1 Deactivating the last active admin returns 409 with a clear error code and leaves the user active.
- [ ] AC2 Demoting the last active admin returns 409, also when other admins exist but are inactive.
- [ ] AC3 With two active admins, deactivating or demoting one is allowed.
- [ ] AC4 The UI shows the pt/en message and disables the control for the last active admin.
- [ ] AC5 A Postgres integration test covers AC1-AC3.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

After AE-0514 (same admin dialog files) and AE-0528 (#322).

## Progress Log

### 2026-10-31

Ticket filed from the AE-0528 review. No product decision needed (safety rule).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
