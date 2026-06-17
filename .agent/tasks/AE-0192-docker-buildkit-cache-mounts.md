# AE-0192 — Docker: BuildKit cache mounts for uv sync + npm ci

Status: Ready
Tier: T1
Priority: Medium
Type: Task
Area: Backend/DevOps
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Faster droplet rebuilds via BuildKit cache mounts (deploy uses `up -d --build`).

## Problem
Source: kaizen production-readiness sweep. No `--mount=type=cache` on dependency installs.

## Scope
- Backend builder: `RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev`.
- Frontend deps: `RUN --mount=type=cache,target=/root/.npm npm ci`.
- Confirm BuildKit enabled in deploy.

## Non-Goals
- Image-size changes (covered by AE-0190/0191).

## Acceptance Criteria
- [ ] Cache mounts added; warm rebuild is materially faster (record timing).
- [ ] Builds still reproducible/locked.

## Gherkin Scenarios
```gherkin
Feature: Cached dependency installs
  Scenario: warm rebuild reuses cache
    Given BuildKit cache mounts on uv sync / npm ci
    When an unrelated source file changes and the image rebuilds
    Then dependencies are not re-downloaded
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
