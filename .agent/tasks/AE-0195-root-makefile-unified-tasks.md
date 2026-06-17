# AE-0195 — Add root Makefile for unified build/test/lint (polyglot task runner)

Status: Ready
Tier: T2
Priority: Medium
Type: Task
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
One entry point for both stacks without restructuring either.

## Problem
Source: kaizen production-readiness sweep. No root task runner; commands are ad hoc
per project. A root Makefile/just unifies polyglot (uv + npm) commands. (npm/pnpm
workspaces / Nx / Turborepo rejected — JS-only, won't unify Python; over-engineering.)

## Scope
- Root `Makefile` (or `Justfile`) with `setup/build/test/lint/typecheck/dev`
  delegating to `cd backend && uv run ...` and `cd frontend && npm run ...`.
- README "Repository layout & unified commands" section.

## Non-Goals
- npm/pnpm workspaces; Nx/Turborepo/Bazel; uv workspace (single package).

## Acceptance Criteria
- [ ] `make test` / `make lint` / `make build` run both stacks correctly.
- [ ] README documents the targets.

## Gherkin Scenarios
```gherkin
Feature: Unified commands
  Scenario: make test runs both stacks
    Given the root Makefile
    When `make test` runs
    Then backend pytest and frontend vitest both execute
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
