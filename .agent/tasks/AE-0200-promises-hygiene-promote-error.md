# AE-0200 — Frontend: promises-hygiene — fix floating/misused promises then promote to error

Status: Done
Tier: T2
Priority: High
Type: Refactor
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Eliminate the 30 async-correctness warnings (likely real bugs) and lock them as errors.

## Problem
Source: kaizen production-readiness sweep. 16 `no-floating-promises` + 14 `no-misused-promises`
remain at warn (currently --quiet-suppressed). All mechanically fixable (`void`,
sync-arrow wrappers) without behavior change. (Note: PR #28 fixed a prior batch on another branch.)

## Scope
- Fix all 16 + 14 root-cause (no suppressions): `void invalidateQueries(...)`,
  `onClick={() => { void handler() }}`.
- Then flip BOTH rules warn→error in eslint.config.mjs.

## Non-Goals
- Disabling/suppressing any case.

## Acceptance Criteria
- [ ] 0 floating/misused-promise findings; both rules error; tests green.
- [ ] **Seeded floating promise ERRORS**; seeded `refetch()` is unaffected.

## Gherkin Scenarios
```gherkin
Feature: Async correctness enforced
  Scenario: new floating promise blocked
    Given both rules promoted to error after burn-down
    When a hook leaves a promise unhandled
    Then lint fails
```

## Delta
### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...

## Affected Areas
- Frontend:
- Docs:
- Tests:

## Dependencies
- Blocks:
- Blocked by:
- Related:

## Implementation Plan
1. See Scope.

## QA Checklist
- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log
### 2026-06-17 00:00
Emitted by kaizen production-readiness sweep (.agent/reports/kaizen-production-readiness.plan.md).

### 2026-06-17 (executed, dev→QA loop, PR #31)
DONE — 32 floating/misused promises fixed; both promoted to error [commit 47d8a00]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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

Promises-hygiene fixed; `no-floating-promises` + `no-misused-promises` promoted to error. Verified in main.
