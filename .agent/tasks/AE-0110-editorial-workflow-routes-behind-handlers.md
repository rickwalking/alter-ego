# AE-0110 — Workflow start/state/resume routes behind editorial handlers (byte-identical API + SSE)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0110-editorial-workflow-routes
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move `editorial_workflow.py` start/state/resume (+ stream) endpoint logic behind editorial application handlers via the facade; routes become thin adapters. Workflow API + SSE byte-identical; LangGraph checkpoint identifiers + schemas stable; agents/engine wrapped, not replaced.

## Problem

Workflow routes construct the orchestrator/service/engine directly and mutate the carousel row. They must delegate to the editorial facade + ACL with no behavior change, building on AE-0044's response mapper.

## Scope

- Each workflow endpoint (state/start/resume/stream) delegates to an editorial handler via the facade, resolved by a get_editorial_service edge DI provider (mirror api/dependencies/knowledge.py + conversation.py).
- Preserve the workflow state response (build on AE-0044's mapper), SSE event types/framing/keep-alive/Last-Event-ID, status codes, and `X-Agent-Origin`/headers EXACTLY.
- Keep LangGraph checkpoint identifiers (thread_id=project_id) + CarouselWorkflowState schema + interrupt payloads unchanged (wrap the existing engine/orchestrator).
- Writes via the platform UoW + the AE-0107 single owner; routes stop calling db.commit() / get_container for workflow ops.

## Non-Goals

- No source/assignments/review/optimistic-lock port move yet (AE-0111).
- No checkpoint/SSE schema change.
- No presentation/CRUD route change.

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] EACH workflow endpoint (state/start/resume/stream) SHALL delegate via the editorial facade + handlers (thin adapter routes)
- [ ] WHEN a workflow endpoint is called THE response + SSE stream SHALL diff to ZERO against the AE-0106 snapshots (types/framing/keep-alive/Last-Event-ID)
- [ ] THE workflow routes SHALL NOT import carousel ORM models or get_container, and SHALL NOT call db.commit() directly (UoW single committer via the AE-0107 owner)
- [ ] THE LangGraph checkpoint identifiers + CarouselWorkflowState schema + interrupt payloads SHALL be unchanged
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass; AE-0106 safety net green

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0106 safety net (diff=0).

## Delta

### ADDED

- editorial workflow command/query handlers
- api/dependencies/editorial.py edge DI provider

### MODIFIED

- api/routes/carousels/editorial_workflow.py (thin adapters via facade)

### REMOVED

- Direct orchestrator/engine construction + carousel row mutation in the workflow routes

## Affected Areas

- Backend: editorial module
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: editorial workflow routes
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0111, AE-0112
- Blocked by: AE-0106, AE-0107, AE-0108, AE-0109
- Related: AE-0044, AE-0045, AE-0046, AE-0041, AE-0104

## Implementation Plan

1. Add get_editorial_service edge provider.
2. Move state/start/resume/stream logic into editorial handlers wrapping the engine via the ACL.
3. Verify checkpoints stable + safety net diff=0. GATE: AE-0041/0044/0045/0046 merged first.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

Dev Complete (Wave C). editorial_workflow.py thin adapters via EditorialWorkflowHandlers + api/dependencies/editorial.py edge provider; byte-identical (AE-0106 19/19); checkpoints stable; no route commit; mypy 478, lint-imports 14/0, ratchet api->infra 82→81, check-integrity 0 blockers, 726 carousel tests pass.

## Files Touched

api/routes/carousels/editorial_workflow.py, api/dependencies/editorial.py (new), modules/editorial/application/workflow_handlers.py (new), modules/editorial/infrastructure/legacy_carousel_acl.py, modules/editorial/{public,__init__}.py, tests/unit/modules/editorial/test_workflow_handlers.py

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

HARD GATE (Wave C): AE-0041, AE-0044, AE-0045, AE-0046 (PASS QA, in Review) touch the same
carousel workflow files (esp. `editorial_workflow_routes_response.py`, the AE-0044 response mapper this
ticket builds on). They MUST be merged before AE-0110 redirects the workflow routes, or this ticket must
explicitly own the current state of those files to avoid double-refactoring.

## Final Summary

Pending.
