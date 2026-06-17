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

### 2026-06-17 (executed, dev→QA loop, PR #31)
PARTIAL — chromium single-layer install done; visual export check pending on droplet [commit d350554]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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


### 2026-06-17 (architect validation — user's 'Playwright CLI' idea)
Validated: the literal 'use the CLI' framing is a misconception, but the instinct is right.
Real lever = `playwright install --with-deps --only-shell` (chromium-headless-shell, not full headed).
Basis: since Playwright v1.49 `install chromium` ships BOTH builds and headless auto-uses the shell;
this app is 100% headless + builds PDFs via img2pdf (no page.pdf()), so the headed binary is dead weight
(~60-90MB). Applied the one-line change. Risk Low. REMAINING (this ticket's open AC): pixel-diff a
carousel export on staging before prod. Bigger ~1GB win (sidecar/connect_over_cdp) deferred as a future T3.
