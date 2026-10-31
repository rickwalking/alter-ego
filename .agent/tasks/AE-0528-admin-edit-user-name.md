# AE-0528 — Admin edits a user's name

Status: In Development
Tier: T1
Priority: Medium
Type: Feature
Area: Full-stack
Owner: Pedro
Agent Lane: developer → qa → release
Branch: feat/ae-0528-admin-edit-user-name
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

> Listed by Pedro as "AE-0510" (users area); repo id AE-0528 reserved in the
> 2026-10-22 triage (AE-0510 in the repo is an older chat ticket).

## Goal

On `/admin/users`, the edit dialog lets an admin change a user's full name. The
email stays fixed (owner decision in the 2026-10-22 triage, question 11).

## Problem

Finding DQ-D-02: `frontend/src/components/admin/edit-user-dialog.tsx` sends only
`{role, is_active}` and the backend `PATCH /api/admin/users/{id}` builds
`UpdateUserInput(role, is_active)`, so a misspelled name can only be fixed in the
database.

## Scope

- Backend: optional `full_name` on `UpdateUserRequest` (whitespace stripped,
  1..255 chars, else 422), carried by `UpdateUserInput` and applied by
  `AdminUserHandler.update` through a `User.rename` mutator that bumps
  `updated_at`. The `users.full_name` column already exists and the repository
  already persists it: no DB or migration change.
- Frontend: labelled "Nome completo"/"Full name" field in the edit dialog,
  pre-filled, trimmed, validated before submit (pt/en message), sent only when
  changed; a 422 validation error maps to the same message.
- OpenAPI artifact regenerated.

## Non-Goals

- Editing the email (stays fixed; no email field anywhere in the edit path).
- Audit trail: the admin update handler emits no audit event or log line today,
  so there is nothing to extend (AC6 follows the existing behaviour).

## Acceptance Criteria

- [x] AC1 Given the admin opens the edit dialog for a user, Then a labelled
  "Nome completo"/"Full name" field shows the current name and is editable;
  saving sends the new name via the existing `PATCH /api/admin/users/{id}`, and
  the table shows the new name.
- [x] AC2 The name is trimmed; blank (after trim) or longer than 255 chars is
  rejected: the backend answers 422 (Pydantic validation on the request schema),
  and the dialog shows a pt/en validation message before submit (and maps a 422
  to the same message).
- [x] AC3 Omitting the name in the PATCH leaves it unchanged (existing
  role/is_active-only callers keep working).
- [x] AC4 The email is NOT editable (no email field in the edit dialog; the API
  ignores an email field — none is added to the schema).
- [x] AC5 Admin-only: a non-admin gets 403 (existing admin dependency); an
  unknown id 404 as today. The last-admin / self-demotion rules still hold when
  the name is edited together with role.
- [x] AC6 The change is audited/logged the same way existing admin user updates
  are (today: no audit event and no log line, so none is added).

## Gherkin Scenarios

- `backend/tests/features/admin_edit_user_name_ae0528.feature`
- `frontend/tests/features/admin-edit-user-name-ae0528.feature`

## Delta

### ADDED

- `User.rename`, `UpdateUserInput.full_name`, `UpdateUserRequest.full_name`.
- Edit-dialog name field, client validation, `nameInvalid` pt/en strings.

### MODIFIED

- `AdminUserHandler.update` applies the name; `docs/architecture/openapi.json`.

### REMOVED

- None.

## Affected Areas

- Backend: identity admin handler, admin route schema, `User` aggregate.
- Frontend: `edit-user-dialog.tsx`, i18n.
- Database: none (`users.full_name` exists).
- API: `PATCH /api/admin/users/{id}` accepts optional `full_name`.
- Tests: handler unit tests, API integration tests, dialog tests.
- Docs: OpenAPI artifact.
- Prompts/LLM: none.
- Observability: none (no existing audit/log on admin updates).
- Deployment: none.

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0491 (users area base), AE-0515 (search/filter users)

## Implementation Plan

1. Gherkin (backend + frontend).
2. Backend schema, command, handler, aggregate mutator, tests, OpenAPI export.
3. Frontend field, validation, i18n, tests.
4. Full gates, dev summary, move to Dev Complete.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-31 10:00

Ticket written; implementation started on `feat/ae-0528-admin-edit-user-name`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- The name is applied through a new `User.rename` aggregate mutator so it bumps
  `updated_at` like `set_role`/`activate` do.
- The dialog sends `full_name` only when the trimmed value differs from the
  current name, so a role-only save keeps the old request shape.

## Blockers

None.

## Final Summary

Pending.
