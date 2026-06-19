# AE-0228 — Admin module TanStack Query layer + migrate admin user management

Status: Intake
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread A1). Extends AE-0184 (fetch) + AE-0187 (Suspense).

## Goal

Create a `src/modules/admin/` TanStack Query layer and migrate admin user
management off raw `fetch` + manual `isLoading`, closing the largest fetch
cluster and the one large ADR-010 initial-load violation in one move.

## Problem

The admin user area is the convergence point of two migrations (verified by scan):
- 5 of 7 raw `fetch(` violations live here: `app/(admin)/admin/users/page.tsx:28`
  (GET in a `useEffect`) + the 4 `components/admin/*-dialog.tsx` (create/edit/
  delete/reset-password mutations).
- `users/page.tsx` also violates ADR-010: initial data load via `useState(isLoading)`
  + `useEffect(fetch)` + `if (isLoading) return <spinner>` instead of Suspense.
There is no `src/modules/admin/` module yet; the pattern to follow is
`src/modules/identity/{queries.ts,hooks/}` over the central `src/lib/api-client.ts`.
`QueryProvider` is already configured.

## Scope

- New `src/modules/admin/queries.ts` (`adminKeys`, query + mutation options) and
  `hooks/use-admin-users.ts` (1 list query as `useSuspenseQuery` + 4 mutations).
- `users/page.tsx`: drop manual loading; `useSuspenseQuery` + wrap the table in
  `<Suspense>` (+ error boundary).
- 4 dialogs: `useMutation`; keep pending UX via `mutation.isPending` (legit).

## Non-Goals

- No change to server-side authz or the /api/admin endpoints (client data-layer only).
- Do not migrate non-admin components (separate tickets A2).

## Acceptance Criteria

- [ ] 0 raw `fetch(` in `components/admin/**` and `app/(admin)/admin/users/page.tsx` (eslint fetch rule green).
- [ ] Users list loads via `useSuspenseQuery` + `<Suspense>`; no manual `isLoading` initial-load branch.
- [ ] All admin CRUD behavior preserved (create/edit/delete/reset-password).
- [ ] MSW-backed hook unit tests for the query + 4 mutations.
- [ ] `bash scripts/ci/gates.sh frontend` green; `check-integrity.sh frontend` 0 net-new.

## Classification (AE-0153)

Behavior-preserving refactor of the data layer (no user-visible behavior change) —
unit/integration tests suffice; assert identical request shapes + UI states.

## Dependencies

- Blocks: AE-0229 (shares the established Suspense+Query pattern), the optional Suspense-lint ratchet.
- Related: AE-0184, AE-0187.

## Progress Log

### 2026-06-18
Created from the architect plan (Thread A1).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
