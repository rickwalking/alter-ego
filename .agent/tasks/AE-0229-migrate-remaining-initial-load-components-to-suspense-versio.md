# AE-0229 — Migrate remaining initial-load components to Suspense

Status: Intake
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread A2). Extends AE-0187 (Suspense ratchet).

## Goal

Convert the remaining genuine initial-data-load components to the ADR-010 pattern
(Server Components + TanStack Query + `useSuspenseQuery`/`<Suspense>`), driving the
initial-load violation count to zero.

## Problem

Two remaining cases (verified by scan; most other `isLoading` are LEGIT mutation flags):
1. `modules/publishing/blog/components/version-history-sidebar.tsx` — `useEffect` +
   `useState(loading)` + `{loading && ...}` for an initial load.
2. `modules/publishing/distribution/components/regenerate-strategy-section.tsx` —
   MIXED: has a `<Suspense>` boundary but uses `useQuery` (so it never suspends) +
   a manual `if (isLoading)` branch. The boundary is dead.

## Scope

- version-history-sidebar: replace with `useSuspenseQuery` + parent `<Suspense>`.
- regenerate-strategy-section: switch `useAvailableStrategies()` → a `useSuspenseQuery`
  variant; remove the manual `if (isLoading)/isError` branch; keep the regenerate
  **mutation** as-is.

## Non-Goals

- Do not touch mutation pending flags anywhere (ADR-010 allows them).
- Do not invent new endpoints.

## Acceptance Criteria

- [ ] Both components load initial data via `useSuspenseQuery` under a `<Suspense>` boundary.
- [ ] No manual initial-load `isLoading` branch remains in either file.
- [ ] regenerate-strategy mutation behavior unchanged.
- [ ] `bash scripts/ci/gates.sh frontend` green.

## Classification (AE-0153)

Behavior-preserving refactor (loading UX equivalent) — unit tests suffice.

## Dependencies

- Blocked by: AE-0228 (settles the Suspense+Query pattern). Can parallelize once that lands.
- Related: AE-0187.

## Progress Log

### 2026-06-18
Created from the architect plan (Thread A2).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
