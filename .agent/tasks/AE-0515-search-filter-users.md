# AE-0515 — Search and filter users

Status: Dev Complete
Tier: T1
Priority: Low
Type: Feature
Area: Frontend (admin users area)
Owner: Pedro
Agent Lane: developer → qa
Branch: feat/ae-0515-search-filter-users
Kanban Card: TBD
Created: 2026-10-30
Updated: 2026-10-31

## Goal

On `/admin/users`, an admin can narrow the user list with a "Buscar"/"Search"
field (name or email, case- and accent-insensitive, client-side over the fetched
list, which is capped at 1000 users by the backend) plus role and status
filters, with a clear message when nothing matches.

## Problem

The users area (AE-0491 base merged) lists every user with no way to search or
filter (finding DQ-D-03). Admins with many users must scan the whole table.

## Scope

- A filter toolbar above the users table: search textbox (type="search",
  labelled), role select (all/admin/editor), status select (all/active/inactive).
- Pure filtering helper in `src/lib/` with accent- and case-insensitive
  normalization (NFD + diacritic strip + lowercase), unit-tested.
- Empty-filter-result message distinct from the "no users at all" message.
- Keyboard accessible via native labelled controls; pt/en strings.
- Client-side only; the backend list cap (1000) is unchanged.

## Non-Goals

- Server-side search/pagination (backend stays as-is).
- Editing names/emails (AE-0528 was never built; not in scope).
- Dialog modality, mobile layout, theming (AE-0514).
- Changing the row actions or the create/edit/delete/reset flows.

## Acceptance Criteria

- [x] AC1 Given the admin is on `/admin/users`, When they type in "Buscar",
  Then rows filter by name or email, case- and accent-insensitively
  (e.g. "joao" matches "João", "JOSE" matches "José").
- [x] AC2 Given the admin picks a role filter (admin/editor), Then only rows
  with that role show; "All roles" shows every role.
- [x] AC3 Given the admin picks a status filter (active/inactive), Then only
  rows with that status show; "All statuses" shows every status.
- [x] AC4 Given filters combine (search + role + status), Then rows must match
  all active filters.
- [x] AC5 Given no row matches the active filters, Then a "no users match the
  filters" message shows instead of the table.
- [x] AC6 Given the admin clears the filters, Then the full list shows again.
- [x] AC7 All controls are native, labelled and keyboard accessible; all
  strings exist in pt and en.

## Gherkin Scenarios

- `frontend/tests/features/admin-users-search-filter-ae0515.feature` (9 scenarios)

## References

- Files: `src/app/(admin)/admin/users/page.tsx`, `src/components/admin/user-table.tsx`
- DQ-D-03 (dashboard QA triage).
- Backend list cap: `backend/src/rag_backend/modules/identity/application/admin_handlers.py` (`_ADMIN_LIST_LIMIT = 1000`).

## Progress Log

### 2026-10-31 12:45

Rebased on main, independent review (no blockers) applied: fixture emails no longer contain the names, so the
search tests prove the name match; empty-list and keyboard (Tab order) scenarios added; the clear test resets role
and status; the status filter has its own `statusLabel` key; the no-match message hides while a fetch error shows.

## Test Evidence

Full local frontend gates at f0341d775: pass 18, fail 0, skip 1 (mutation, CI only). GATES_JSON in
`.agent/reports/AE-0515.dev-summary.md`. Seeded checks: dropping the empty-state guard fails 1 page test; matching
`full_name` without normalization fails 3 tests.

## QA Report

Independent review: no blockers; SHOULD-FIX items 1-4 and NITs 5, 6, 8 applied. NIT 7 (string unions for the filter
values) left as is: the values are constants and the selects only offer those options.
