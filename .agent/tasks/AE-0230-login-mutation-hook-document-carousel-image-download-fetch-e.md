# AE-0230 — Login mutation hook + document carousel image-download fetch exception

Status: Intake
Tier: T1
Priority: Low
Type: Refactor
Area: Frontend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread A3, optional/low priority).

## Goal

Tidy the two remaining fetch sites that are NOT clear violations: standardize login
on a mutation hook, and formally document the carousel image-download fetch as a
sanctioned exception.

## Problem

- `app/login/page.tsx:47` POSTs `/api/auth/token` with raw fetch (NOT eslint-blocked
  — not in a hook). Cosmetic inconsistency vs the `postLogout` mutation pattern.
- `modules/publishing/distribution/components/horizontal-carousel-viewer.tsx:73` uses
  raw fetch to download slide images (one-shot asset download, per-fetch abort/timeout)
  — no TanStack Query benefit; should be a documented exception, not forced into Query.

## Scope

- Add `postLogin` to `modules/identity/queries.ts` + a `useLogin` mutation; use it in login page.
- Document the carousel image-download fetch as a sanctioned non-query exception
  (code comment + a line in the suspense/fetch guide), OR wrap in a small non-query util.

## Non-Goals

- No auth flow/behavior change; same /api/auth/token contract.

## Acceptance Criteria

- [ ] Login uses a mutation hook (or a documented decision to leave it); behavior unchanged.
- [ ] Carousel image-download fetch has an explicit, documented exception rationale.
- [ ] `bash scripts/ci/gates.sh frontend` green.

## Classification (AE-0153)

Behavior-preserving + docs — unit tests suffice.

## Dependencies

- Related: AE-0228, AE-0184.

## Progress Log

### 2026-06-18
Created from the architect plan (Thread A3).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
