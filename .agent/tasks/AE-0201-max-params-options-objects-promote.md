# AE-0201 — Frontend: max-params -> options objects (2 sites) then promote to error

Status: Ready
Tier: T1
Priority: Low
Type: Refactor
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Clear the 2 max-params warnings and lock the rule.

## Problem
Source: kaizen production-readiness sweep. 2 sites exceed max-params
(content-phase-review.tsx, use-blog-ai.ts). CLAUDE.md already mandates <=3 args / param objects.

## Scope
- Refactor both signatures to an options object; update call sites/tests.
- Flip `max-params` warn→error.

## Non-Goals
- Other complexity rules.

## Acceptance Criteria
- [ ] 0 max-params findings; rule error; tests green.
- [ ] **Seeded 4-arg function ERRORS.**

## Gherkin Scenarios
```gherkin
Feature: Param-count enforced
  Scenario: 4-arg function blocked
    Given max-params promoted to error
    When a function declares 4 positional params
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
DONE — 5 max-params → options objects; promoted to error [commit 47d8a00]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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
