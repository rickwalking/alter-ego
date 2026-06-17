# AE-0198 — Frontend: fix duplicate-value exports in constants/neon.ts (knip)

Status: Ready
Tier: T1
Priority: Low
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Resolve the one real knip finding.

## Problem
Source: kaizen production-readiness sweep (live knip run). `frontend/src/constants/neon.ts`
has duplicate-value exports `NEON_BORDER_FOCUS` / `NEON_PERSONA_AVATAR_BORDER`.

## Scope
- Collapse to a single source-of-truth constant; update importers.

## Non-Goals
- The dead-file (AE-0158) / dep (AE-0183) work.

## Acceptance Criteria
- [ ] knip reports 0 duplicate exports; importers updated; tests/build green.

## Gherkin Scenarios
```gherkin
Feature: No duplicate constants
  Scenario: single source of truth
    Given the two duplicate-value exports
    When collapsed to one
    Then knip duplicates = 0 and behavior is unchanged
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
DONE — neon.ts duplicate export removed [commit 47d8a00]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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
