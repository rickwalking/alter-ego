# AE-0202 — Frontend: migrate img->next/image, fix dead exemption glob, promote no-img-element

Status: Ready
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Remove raw <img>, fix a stale eslint exemption, and lock the rule.

## Problem
Source: kaizen production-readiness sweep. 7 prod `<img>` flagged. The eslint exemption glob
`src/features/blog/components/public-post/**` is DEAD (files moved to
`src/modules/publishing/blog/components/public-post/**`), so it exempts nothing.

## Scope
- Fix/remove the stale exemption glob in eslint.config.mjs.
- Migrate the 7 `<img>` to `next/image` (set dimensions / remotePatterns; test layout).
- Flip `@next/next/no-img-element` warn→error.

## Non-Goals
- Unrelated image refactors.

## Acceptance Criteria
- [ ] 0 no-img-element findings; rule error; layouts visually unchanged; tests/build green.
- [ ] **Seeded `<img>` ERRORS.**

## Gherkin Scenarios
```gherkin
Feature: next/image enforced
  Scenario: raw img blocked
    Given the rule promoted to error and the glob fixed
    When a component uses <img>
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
