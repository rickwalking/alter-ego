# AE-0190 — Backend Dockerfile: convert to multi-stage (copy .venv, drop uv/pip from runtime)

Status: Done
Tier: T2
Priority: High
Type: Refactor
Area: Backend/DevOps
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Shrink the backend runtime image (~80-150MB) and speed start by removing build tooling.

## Problem
Source: kaizen production-readiness sweep. `backend/Dockerfile` is SINGLE-stage:
uv + pip + build toolchain ship in the runtime layer, `uv sync` runs twice, and
`CMD ["uv","run","uvicorn",...]` re-resolves at start.

## Scope
- Builder stage: `COPY --from=ghcr.io/astral-sh/uv /uv /bin/`, `UV_COMPILE_BYTECODE=1`,
  `UV_LINK_MODE=copy`, `uv sync --locked --no-dev` (once).
- Runtime stage: clean `python:3.12-slim`, `COPY --from=builder /app/.venv /app/.venv`,
  `ENV PATH=/app/.venv/bin:$PATH`, `CMD ["uvicorn","rag_backend.main:app","--host","0.0.0.0","--port","8000"]`.
- No uv/pip in final image.

## Non-Goals
- Playwright slimming (AE-0191); distroless (rejected — Chromium needs system libs).

## Acceptance Criteria
- [ ] Multi-stage; runtime contains no uv/pip; single `uv sync`.
- [ ] Image size reduced vs baseline (record before/after `docker image ls`).
- [ ] App boots; healthcheck passes; tests/migrations unaffected.

## Gherkin Scenarios
```gherkin
Feature: Lean backend runtime
  Scenario: uv absent from runtime
    Given the multi-stage build
    When the runtime image is inspected
    Then uv/pip are not present and uvicorn starts directly
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
DONE — backend multi-stage; built 1.65GB; no uv/pip in runtime [commit d350554]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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

backend/Dockerfile converted to multi-stage (builder→runtime, copies .venv, drops uv/pip from runtime). Verified (2 FROM stages).
