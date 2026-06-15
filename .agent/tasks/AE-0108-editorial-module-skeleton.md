# AE-0108 — modules/editorial skeleton + facade + EditorialProject/EditorialWorkflow + status language + ports

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0108-editorial-module
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Create `modules/editorial/` (domain/application/infrastructure/api + public.py + bootstrap.py + constants.py); define EditorialProject/EditorialWorkflow domain entities + the workflow status language (re-exporting the existing `domain/constants/carousel_workflow.py`); re-export the carousel repository port. No routes moved yet.

## Problem

There is no editorial module/facade today; the module skeleton + domain + status language + ports must exist before the ACL (AE-0109) and route delegation (AE-0110).

## Scope

- Scaffold modules/editorial per conventions + _template (mirror modules/conversation).
- Define EditorialProject / EditorialWorkflow domain entities + workflow status value objects; re-export the existing carousel workflow status constants (no new strings).
- Re-export the carousel repository port (object-identity shim) + relevant entities so existing callers keep resolving.
- public.py facade + bootstrap.py (manual DI, no get_container); reuse platform/database UoW.

## Non-Goals

- No routes/ACL moved (AE-0109/0110).
- No agent/workflow behavior change.
- No presentation extraction.

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] modules/editorial SHALL exist per conventions with public.py facade + bootstrap.py (manual DI, no get_container)
- [ ] EditorialProject/EditorialWorkflow + workflow status value objects SHALL be typed (no Any) and re-export the existing carousel workflow status constants (no new status strings)
- [ ] THE carousel repository port + relevant entities SHALL be re-exported via object-identity shims (existing callers keep resolving; CI-verified)
- [ ] THE module SHALL reuse the platform/database UoW (no new UoW)
- [ ] WHEN mypy/lint-imports/pytest run THEY SHALL pass with no new violations and no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving scaffolding; verified by mypy/lint-imports + AE-0106 safety net.

## Delta

### ADDED

- modules/editorial/{domain,application,infrastructure,api}/, public.py, bootstrap.py, constants.py
- EditorialProject/EditorialWorkflow domain entities + status value objects

### MODIFIED

- None (canonical Protocols/constants stay; re-export only)

### REMOVED

- None

## Affected Areas

- Backend: editorial module
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none yet
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0109, AE-0110, AE-0112
- Blocked by: None
- Related: AE-0081, AE-0100, AE-0104

## Implementation Plan

1. Scaffold modules/editorial from _template.
2. Define EditorialProject/EditorialWorkflow + re-export status constants.
3. Re-export repo port/entities; bootstrap; mypy/lint-imports.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

Dev Complete (Wave A). modules/editorial skeleton + facade + bootstrap (manual DI, no get_container); EditorialProject/EditorialWorkflow domain entities + status value objects re-exporting carousel_workflow constants (object-identity, no new strings); CarouselRepository + entity shims; reuses platform UoW. mypy 474, lint-imports 14/0, 11 unit tests. Wave A combined 47 passed; mypy 474, lint-imports 14/0, integrity 0 blockers.

## Files Touched

backend/src/rag_backend/modules/editorial/** (+public.py/bootstrap.py/constants.py/domain/status.py), tests/unit/modules/editorial/*

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
