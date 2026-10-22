# AE-0491 — Mask the password field in "Criar usuário"

Status: Review
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: fix/ae-0491-mask-create-user-password
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The password an admin types in "Criar usuário" is masked unless the admin chooses to show it, and browsers treat
it as a new password.

## Problem

Dashboard QA (2026-10-22, Users area, security): the create-user password input is `type="text"`
(`frontend/src/components/admin/create-user-dialog.tsx:130`), so the new user's password is shown in clear on screen
(shoulder-surfing, screen sharing, recordings) and the browser offers no password handling. An a11y test pinned
`type="text"`.

## Scope

- New `PasswordInput` (admin components): `type="password"` by default, `autocomplete="new-password"`,
  `autocapitalize="none"`, no spellcheck, plus a labelled show/hide toggle button (`type="button"`,
  `aria-controls` the input, accessible name "Mostrar senha" / "Ocultar senha", 44 px wide).
- `CreateUserDialog` uses it; en + pt strings `admin.showPassword` / `admin.hidePassword`.
- A typed password is never echoed in the dialog (only an auto-generated temp password is shown once, as before).

## Non-Goals

- Dialog modality / focus trap / error mapping / mobile layout (AE-0515).
- The login form (`method="post"`, PR #231).

## Acceptance Criteria

- [x] Given the create-user dialog, When the admin types a password, Then the input is `type="password"` with
      `autocomplete="new-password"`.
- [x] Given the masked field, When the admin presses the labelled "Show password" toggle, Then the value is shown
      and the toggle reads "Hide password"; pressing it again masks the value.
- [x] The toggle is a `type="button"` (never submits the form) and names the input it controls.
- [x] Given the admin typed a password and created the user, Then the success message does not contain it.

## Gherkin Scenarios

```gherkin
Feature: The create-user password is masked

  Scenario: The create-user password is masked by default
    Given the admin opens the "Criar usuário" dialog
    When they look at the password field
    Then it is a password input with autocomplete "new-password"
    And its show/hide toggle is a button labelled "Show password"

  Scenario: The admin can show and hide the typed password
    Given the admin typed a password in the "Criar usuário" dialog
    When they press "Show password"
    Then the password is shown as text and the toggle reads "Hide password"
    When they press "Hide password"
    Then the password is masked again

  Scenario: A typed password is never echoed back
    Given the admin typed a password and created the user
    When the API confirms the user was created
    Then the success message does not contain the typed password
```

## Delta

### ADDED

- `frontend/src/components/admin/password-input.tsx`, its tests, `create-user-password-mask.feature`.

### MODIFIED

- `create-user-dialog.tsx` uses `PasswordInput`; the a11y test expects `type="password"`; en/pt strings.

### REMOVED

- The `type="text"` password input.

## Affected Areas

- Backend: none.
- Frontend: admin create-user dialog.
- Database: none.
- API: none.
- Tests: Vitest component tests.
- Docs: none.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: AE-0515 (admin dialogs a11y/i18n pass, same files).
- Blocked by: none (PR #231 adds `method="post"` to the same `<form>`; rebase if it lands first).
- Related: AE-0470 (admin form labels).

## Implementation Plan

1. Feature + failing tests (masked by default, toggle, no echo); flip the a11y test.
2. `PasswordInput` with the toggle; wire it into the dialog; en/pt strings.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-22 17:40

Tests red (3), component added, tests green; lint, typecheck, format clean.

## Files Touched

- frontend/src/components/admin/password-input.tsx (new), create-user-dialog.tsx
- frontend/src/components/admin/create-user-dialog.test.tsx (new), admin-dialogs-a11y.test.tsx
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/create-user-password-mask.feature (new)

## Test Evidence

See `.agent/reports/AE-0491.dev-summary.md`.

## QA Report

`.agent/reports/AE-0491.qa.md`.

## Decision Log

- The toggle changes its accessible name ("Show"/"Hide password") instead of using `aria-pressed`: a pressed
  "Hide password" button reads as a contradiction to screen-reader users.

## Blockers

None.

## Final Summary

Pending.
