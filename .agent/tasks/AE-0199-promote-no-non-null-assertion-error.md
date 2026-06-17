# AE-0199 — Frontend lint: promote no-non-null-assertion to error (zero-churn ratchet)

Status: Done
Tier: T1
Priority: Medium
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Lock prod code clean of non-null assertions (the only zero-churn warn→error promotion).

## Problem
Source: kaizen production-readiness sweep. All 7 `no-non-null-assertion` findings are in
test files; zero in production source. Promoting to error + `off` in the test override is
a pure ratchet (no code churn).

## Scope
- Flip `@typescript-eslint/no-non-null-assertion` warn→error in eslint.config.mjs.
- Add it as `off` in the existing test-file override block.

## Non-Goals
- The behavior-risky rules (no-unnecessary-condition, nullish) — stay warn (would force suppressions).

## Acceptance Criteria
- [ ] Rule is error for prod source; tests excluded; `npm run lint` clean.
- [ ] **Seeded `foo!` in a prod file ERRORS** (prove enforcement); a `!` in a test does not.

## Gherkin Scenarios
```gherkin
Feature: No non-null assertions in prod
  Scenario: seeded assertion fails
    Given the rule promoted to error
    When a prod file adds a non-null assertion
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
DONE — no-non-null-assertion promoted to error [commit 47d8a00]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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

`@typescript-eslint/no-non-null-assertion` promoted to error in frontend/eslint.config.mjs (zero-churn ratchet). Verified in main.
