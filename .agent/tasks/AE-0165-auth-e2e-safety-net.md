# AE-0165 — Frontend: auth e2e safety net (login/logout/refresh/guard) — precondition for identity

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0165-auth-e2e-safety-net
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Add a Playwright auth e2e safety net (login, logout, token refresh, protected-route guard/redirect) BEFORE the identity module relocation, so the otherwise-unverifiable 'byte-identical auth behavior' of AE-0156/0164 is provable.

## Problem

AE-0156 (identity module) relocates auth/session code with 35+ importers across middleware, route handlers, and pages, but the repo has only tests/e2e/auth.setup.ts (no login/logout/refresh/guard e2e). Without a behavior net, the identity relocation can't be proven safe.

## Scope

Author Playwright e2e specs covering: successful login -> authenticated session; logout -> session cleared + redirect; expired/refresh token flow; unauthenticated access to a protected route -> redirect to login; admin-guard behavior. Test the EXISTING behavior (this is the baseline). No app code change.

## Non-Goals

- No app/auth behavior change (tests only — capture current behavior as the baseline).
- Not the identity relocation itself (that is AE-0156/0164).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters"), after Phases 0-7 merged.
See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] Playwright e2e SHALL cover login, logout, token refresh, protected-route guard/redirect, and admin guard against current behavior
- [ ] The e2e suite SHALL pass on the current code (the auth baseline)
- [ ] Wired into CI (or the e2e job) so AE-0156/0164 can prove byte-identical auth behavior

## Gherkin Scenarios

Given a valid user, When they log in, Then a session is established and protected routes load. Given a logged-in user, When they log out, Then the session is cleared and they are redirected to login. Given no session, When a protected route is requested, Then the user is redirected to login. (Captured as the pre-relocation baseline.)

## Dependencies

- Blocks: AE-0156
- Blocked by: —
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 architect-validation round-1 fix).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
