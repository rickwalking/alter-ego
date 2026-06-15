# AE-0091 — Request-scoped Unit of Work for knowledge writes

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0091-request-scoped-uow
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Introduce a request-scoped Unit of Work owning the transaction boundary for Knowledge write operations; remove route-level `.commit()` for those paths; transaction ownership stays with the UoW/caller (ADR-0009).

## Problem

Today routes call `get_container()` and `await db.commit()` directly and repositories rely on caller commits, so there is no single transaction owner. The plan requires a request-scoped UoW for the pilot.

## Scope

- Add a request-scoped `UnitOfWork` (per-request session + commit/rollback) usable by the knowledge command handlers.
- Route knowledge write commands (create/upload/delete/reprocess) through the UoW; commit once at the request boundary.
- Remove `.commit()` from knowledge routes/handlers business logic; repositories do not own transactions (ADR-0009).
- Scope to knowledge writes only (pilot); do not refactor the whole app's session handling.
- This ticket delivers the UoW PRIMITIVE (wrapping the existing request `AsyncSession` as the single commit owner); per-route delegation/commit removal is owned by AE-0092 (avoid double-commit — UoW is the sole committer).

## Non-Goals

- No global session-handling refactor (later phases).
- No behavior change to /api/documents.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Mirrors the plan's transaction policy; the UoW becomes part of the reusable template (AE-0095).

## Acceptance Criteria

- [ ] A request-scoped `UnitOfWork` SHALL exist and be used by knowledge write command handlers
- [ ] WHEN a knowledge write command succeeds THE UoW SHALL commit exactly once at the request boundary
- [ ] WHEN a knowledge write command raises THE UoW SHALL roll back with no partial writes (test)
- [ ] Knowledge routes/handlers business logic SHALL contain no direct `.commit()` (transaction owned by the UoW)
- [ ] WHEN /api/documents write endpoints run THE behavior SHALL be unchanged (AE-0088 safety net passes)
- [ ] mypy strict + full suite green

## Gherkin Scenarios

```gherkin
Feature: Unit of Work transaction boundary

  Scenario: failed ingest rolls back
    Given a document ingest that fails during embedding
    When the command runs under the Unit of Work
    Then no partial document or chunks are persisted
```

## Delta

### ADDED

- request-scoped UnitOfWork
- rollback test

### MODIFIED

- knowledge command handlers + routes (commit via UoW)

### REMOVED

- route-level .commit() for knowledge writes

## Affected Areas

- Backend: UoW + handlers
- Frontend: none
- Database: none
- API: none
- Tests: commit/rollback
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0092, AE-0093
- Blocked by: AE-0089
- Related: ADR-0009

## Implementation Plan

1. Implement request-scoped UoW.
2. Route knowledge writes through it; drop route commits.
3. Rollback/commit tests; safety net green.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 2 breakdown).

## Files Touched

- platform/database/unit_of_work.py; modules/knowledge/{bootstrap,public,application/service}.py; tests/unit/platform + tests/unit/modules/knowledge

## Test Evidence

```
gates.sh backend: 13 PASS / 0 FAIL / 4 SKIP(DB); check-integrity: 0 net-new blockers
mypy 424; lint-imports 10/0; full suite 1757 passed; snapshot diff=0
```

## QA Report

✅ PASS — Phase 2 batch QA (gates.sh + check-integrity reproduced), 2 passes WARN→PASS. See `.agent/reports/AE-0091.qa.md` -> `.agent/reports/phase-2.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
