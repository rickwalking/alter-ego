# AE-0191 — Backend image: slim Playwright (chromium-only, prune apt in one layer)

Status: Ready
Tier: T2
Priority: Medium
Type: Refactor
Area: Backend/DevOps
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Cut ~150-300MB from the backend image by leaning out the Playwright/Chromium install.

## Problem
Source: kaizen production-readiness sweep. `playwright install chromium` +
`install-deps chromium` pull a broad apt set; lists/caches linger. Chromium is the
dominant size driver (Playwright is runtime-critical: carousel export + research scraping).

## Scope
- In the runtime stage, install chromium + deps in ONE `RUN` ending with
  `apt-get clean && rm -rf /var/lib/apt/lists/*`.
- Evaluate `chromium-headless-shell` instead of full chromium.

## Non-Goals
- Removing Playwright (it is runtime-critical).

## Acceptance Criteria
- [ ] Single-layer install + apt cleanup; image smaller (record before/after).
- [ ] **Carousel PDF/image export verified visually unchanged** (fonts/rendering) — if headless-shell regresses, keep full chromium.
- [ ] Research scraping path still works.

## Gherkin Scenarios
```gherkin
Feature: Slim Playwright layer
  Scenario: export still renders after slimming
    Given chromium-only install with apt pruned
    When a carousel is exported
    Then the output is visually identical to baseline
```

## Delta
### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...

## Affected Areas
- Backend:
- Frontend:
- Tests:
- Docs:
- Deployment:

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
