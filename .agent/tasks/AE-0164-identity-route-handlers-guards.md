# AE-0164 — Frontend: relocate auth route handlers + guards behind the identity contract

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0164-identity-route-handlers-guards
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Second identity slice: route the auth route handlers (app/api/auth/*) + route-level guards (middleware.ts + admin/login guards) through the modules/identity public contract established in AE-0156, keeping App Router paths + auth behavior byte-identical.

## Problem

AE-0156 moves the auth/session CLIENT lib into modules/identity, but the route handlers under app/api/auth/* and the route-level guards (middleware, admin) are route-adjacent and higher-risk; they are split into this separate slice.

## Scope

Route app/api/auth/* handlers + middleware/admin guards through @/modules/identity (the contract from AE-0156); keep the route URLs + redirects + cookie/JWT behavior byte-identical; lean on the AE-0165 auth e2e. No behavior change.

## Non-Goals

- No App Router URL/route-handler path change; no auth behavior change.
- The shared HTTP client (authenticated-fetch/server-fetch) stays in lib/ as platform infra (NOT moved into identity).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters"), after Phases 0-7 merged.
See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] app/api/auth/* + middleware/admin guards SHALL go through the @/modules/identity contract
- [ ] App Router URLs, redirects, cookie/JWT behavior byte-identical; AE-0165 auth e2e green
- [ ] typecheck + lint (boundary 0/0) + 822 unit tests + build + check:legacy green

## Gherkin Scenarios

Not applicable — behavior-preserving relocation; verified by the AE-0165 auth e2e + the green-gate safety net.

## Dependencies

- Blocks: —
- Blocked by: AE-0156
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
