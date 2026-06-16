# AE-0144 — Component-type-location gate with baseline ratchet (the 13x class)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0144-component-type-location-gate
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

PR #21 (Phase 7) review follow-up. Component-type-location gate with baseline ratchet (the 13x class).

## Problem

PR #21 review (flagship): component prop types/interfaces are defined inconsistently — ~13 components define their Props types in a location that diverges from the convention (co-located in the component file or a sibling types file). Needs an enforced, ratcheted convention so the 13x class shrinks, not grows.

## Scope

Add a gate (eslint rule or a scripts/ checker like the boundary ratchet) that enforces the component-type-location convention, grandfathering the existing ~13 violations via a committed down-only baseline; demonstrate+revert a violation. Pick the convention deliberately (document it). Behavior-preserving (type-only).

## Non-Goals

- No behavior change beyond the stated fix.
- No App Router URL changes; existing green gates stay green.
- No gate-gaming (no eslint-disable/@ts-ignore/.skip/lowered thresholds/baseline additions beyond a documented down-only ratchet).

## Modularization Alignment (2026-06-16)

PR #21 (Phase 7 frontend alignment) review fix. Behavior-preserving; holds the Phase 7 green-gate safety net
(typecheck + eslint + lint:boundaries 0 + url:check 26 + lint:circular 0 + Vitest 822 + check:legacy + prettier
format) and the boundary ratchet (down-only). See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] A gate SHALL enforce the component-type-location convention with a committed baseline (the ~13x class grandfathered)
- [ ] The baseline SHALL be down-only (0 new); a demonstrated+reverted violation proves enforcement
- [ ] The convention SHALL be documented; type-only, no behavior change; all gates green

## Gherkin Scenarios

Not applicable — lint/CI/docs/dependency fix; verified by the green-gate safety net.

## Dependencies

- Blocks: —
- Blocked by: AE-0134
- Related: AE-0142

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created from PR #21 review.

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
