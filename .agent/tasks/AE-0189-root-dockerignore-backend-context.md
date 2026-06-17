# AE-0189 — Add root .dockerignore to fix backend build context (1.2GB upload)

Status: Ready
Tier: T1
Priority: High
Type: Task
Area: Backend/DevOps
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Stop uploading ~1.2GB to the Docker daemon on every backend build.

## Problem
Source: kaizen production-readiness sweep. The backend service builds with
`context: .` (docker-compose), but only `backend/.dockerignore` exists — it does
NOT apply to a root context. So `frontend/node_modules` (~1.1GB), `.next`, root
`*.png` (~7MB), `.git`, docs get sent to the daemon each build.

## Scope
- Add `/.dockerignore` excluding: `frontend/node_modules`, `frontend/.next`,
  `**/.venv`, `**/__pycache__`, `.git`, `*.png`, `docs/`, `tmp/`, `backend/tests/`,
  `.env*`, caches. Keep paths the backend image actually needs.

## Non-Goals
- Changing the Dockerfiles (AE-0190/0191).

## Acceptance Criteria
- [ ] `/.dockerignore` present; backend build context drops to a few MB (verify with `docker build` context size or `du`).
- [ ] Backend image still builds and runs (smoke).
- [ ] No secrets/junk in context.

## Gherkin Scenarios
```gherkin
Feature: Lean backend build context
  Scenario: node_modules is not uploaded
    Given context: . for the backend image
    When docker build runs
    Then frontend/node_modules is excluded by the root .dockerignore
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
DONE — root .dockerignore (context ~1.2GB→~40MB) [commit d350554]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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
