# AE-0514 — Users area polish

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Full-stack
Owner: Pedro
Agent Lane: developer → qa → release
Branch: feat/ae-0514-users-area-polish
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

> Listed by Pedro as a users-area item (2026-10-22 triage).

## Goal

The `/admin` users area behaves and looks like the dashboard: real modal
dialogs, messages in the reader's language, a layout that works at 390 px,
readable badges and placeholders, tappable buttons and the PT/EN switch.

## Problem

Findings from the 2026-10-22 dashboard QA triage (users area):

- DQ-D-05: Escape does not close the create-user dialog; the admin dialogs are
  a plain `div.fixed` with no `role="dialog"` and no focus trap.
- DQ-D-06 / DQ-D-11: backend English error strings show raw in the PT UI
  (duplicate email, the generic "Falha ao criar usuário" for a 422, no password
  minimum before submit, "User account is deactivated" on the PT login page);
  no PT/EN switch in the `/admin` shell.
- DQ-D-07: `/admin/users` overflows at 390 px (always-on sidebar, `p-8`,
  `overflow-hidden` table with `whitespace-nowrap` cells, dialog wider than the
  viewport).
- DQ-D-08: the "editor" role badge and the dialog placeholders fail WCAG AA
  contrast; the admin area uses light gray-on-white styles.
- DQ-D-10: row action buttons are about 39 x 20 px on mobile (< 44 px).

## Scope

- Admin dialogs (create, edit, reset password, delete) built on `NeonModal`.
- Stable error `code` on the duplicate-email 409, the last-admin and
  self-delete 409s and the deactivated-account 401; the frontend maps status +
  code to pt/en messages and never shows the English `detail`.
- `/admin` uses the dashboard app shell (`NeonAppShell`): sidebar drawer below
  lg, EN/PT switch, dark neon tokens.
- User rows stack as cards on a phone; the table scrolls inside its own box.
- Role badge and placeholders meet AA; row and dialog buttons >= 44 px.

## Non-Goals

- The last-active-admin guard (AE-0585).
- The no-JavaScript login fallback (`/auth/login`) keeps its generic
  translated invalid-credentials message for a deactivated account.

## Acceptance Criteria

- [x] AC1 Every admin dialog (create, edit, delete, reset password) is a real
  modal: `role="dialog"` (`alertdialog` for delete), `aria-modal`, labelled by
  its title, focus trap, Escape closes, focus returns to the opener.
- [x] AC2 Backend errors are shown as pt/en messages: duplicate email (409),
  422 field errors mapped to the field (password minimum shown up front as
  helper text), deactivated-account login message; mapped by HTTP status + a
  stable error code added to the backend responses (status and `detail` kept).
- [x] AC3 `/admin` works at 390 px: the sidebar is a drawer (menu button,
  Escape/overlay closes, focus handled), user rows stack as cards, no
  page-level horizontal scroll, dialogs fit the viewport.
- [x] AC4 Role badge and placeholders meet WCAG AA contrast (>= 4.5:1), using
  existing tokens.
- [x] AC5 Touch targets >= 44 px on mobile for row actions and dialog buttons.
- [x] AC6 A PT/EN language switch in the admin shell (the dashboard's
  `LanguageSwitcher` in `NeonSidebar`).
- [x] AC7 Admin area visually aligned with the dashboard theme using existing
  tokens/components (no new design system).
- [x] AC8 No regression of AE-0515 (search/filter) and AE-0528 (edit name)
  tests.

## Gherkin Scenarios

Frontend: `frontend/tests/features/users-area-polish-ae0514.feature`.
Backend: `backend/tests/features/admin_error_codes_ae0514.feature`.

```gherkin
Feature: Users area polish

  Scenario: Escape closes a dialog and focus returns to the opener
    Given the admin opened the create-user dialog with the "Create user" button
    When they press Escape
    Then the dialog closes
    And focus is back on the "Create user" button

  Scenario: A duplicate email shows a translated message
    Given the admin fills the create-user form with an email already in use
    When they submit it and the API answers 409 with code "user_email_exists"
    Then the dialog says "A user with this email already exists." in the reader's language
    And the English API text is not shown
```

## Delta

### ADDED

- Backend: `CodedHTTPException` + handler (`api/middleware/coded_error_handler.py`),
  error codes `user_inactive`, `user_email_exists`, `last_admin`, `self_delete`.
- Frontend: `NeonAppShell` (shared by dashboard and admin layouts),
  `admin-user-errors.ts`, `UserFormField`, `CreatePasswordField`, user cards.

### MODIFIED

- `NeonModal`: optional `role`, `closeLabel`, `useId` title id, scrolls inside
  the viewport.
- Admin dialogs, user table, filter toolbar, role badge, users page, login
  error mapping.

### REMOVED

- `AdminSidebar` (the admin area uses the dashboard sidebar, which already
  lists Users for admins) and its three unused i18n keys.

## Affected Areas

- Backend: `api/routes/admin.py`, `api/routes/auth.py`, `api/constants.py`,
  `bootstrap/app_factory.py`, new middleware module.
- Frontend: `components/admin/*`, `app/(admin)/admin/*`, `app/dashboard/layout.tsx`,
  `components/layout/neon-app-shell.tsx`, `components/molecules/neon-modal.tsx`,
  `app/login/*`, `lib/response-error.ts`, `lib/admin-user-errors.ts`, i18n.
- Database: none.
- API: additive `code` field on four error bodies (status and `detail` unchanged).
- Tests: see Test Evidence.
- Docs: none.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0515, AE-0528, AE-0585

## Implementation Plan

1. Backend error codes + tests.
2. Dialogs on `NeonModal`; error mapping by status + code.
3. Admin layout on the dashboard shell; cards on a phone; tokens.
4. Screenshots and touch-target measurements at 390 px.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-31

Ticket created; implemented on `feat/ae-0514-users-area-polish`. See
`.agent/reports/AE-0514.dev-summary.md`.

## Files Touched

See `.agent/reports/AE-0514.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0514.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- Error codes are additive (`{"detail", "code"}`) through a `CodedHTTPException`
  handler, so existing clients that read `detail` are unaffected.
- The admin area reuses the dashboard shell instead of restyling its own
  sidebar: the drawer, focus handling and EN/PT switch come for free.
- Admin role badge is amber, editor cyan: the dashboard magenta badge measures
  about 4.49:1 on the card, below AA.
- Edit/delete/reset dialogs also stop showing English `detail` (last admin,
  self delete, user gone are translated; anything else uses the dialog's
  translated fallback).

## Blockers

None.

## Final Summary

Pending.
