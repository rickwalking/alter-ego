# AE-0109 — Legacy carousel ACL (compatibility adapter: legacy persistence ↔ editorial concepts)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0109-legacy-carousel-acl
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Implement the legacy carousel anti-corruption layer in modules/editorial/infrastructure: the SINGLE adapter that translates the legacy `carousel_projects` persistence (CarouselProjectModel) to/from the editorial domain (EditorialProject/EditorialWorkflow). Editorial application/domain code never touches carousel ORM directly.

## Problem

Editorial concepts must be decoupled from the legacy carousel ORM. Without one ACL, every handler would couple to CarouselProjectModel and the boundary would leak.

## Scope

- Implement the ACL adapter mapping CarouselProjectModel ↔ EditorialProject/EditorialWorkflow (read + write of workflow-owned fields, via the AE-0107 single owner).
- The ACL is the ONLY editorial code importing carousel ORM models / legacy carousel persistence.
- Preserve lock_version semantics + checkpoint identifiers through the adapter; no behavior change.
- Wire via bootstrap (manual DI; reuse platform UoW + the AE-0107 owner).

## Non-Goals

- No routes moved (AE-0110).
- No second persistence translator.
- No schema change.

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] THE ACL SHALL be the ONLY editorial module code importing carousel ORM models / legacy carousel persistence (enforced by the AE-0112 import contract)
- [ ] THE ACL SHALL map CarouselProjectModel ↔ EditorialProject/EditorialWorkflow for the workflow-owned fields, writing via the AE-0107 single owner
- [ ] THE ACL SHALL preserve `lock_version` optimistic-lock semantics and LangGraph checkpoint identifiers exactly
- [ ] Editorial application/domain code SHALL NOT import carousel ORM models directly (only the ACL does)
- [ ] WHEN mypy/lint-imports/pytest + the AE-0106 safety net run THEY SHALL pass (diff=0)

## Gherkin Scenarios

Not applicable — behavior-preserving adapter; verified by the AE-0106 safety net + contract tests.

## Delta

### ADDED

- modules/editorial/infrastructure/legacy_carousel_acl.py (+ adapter tests)

### MODIFIED

- modules/editorial/public.py + bootstrap.py (wire the ACL)

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

- Blocks: AE-0110
- Blocked by: AE-0105, AE-0106, AE-0107, AE-0108
- Related: AE-0104, ADR-0009

## Implementation Plan

1. Map workflow-owned fields per AE-0105.
2. Implement ACL read/write via the AE-0107 owner.
3. Preserve lock_version + checkpoints; contract tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

Dev Complete (Wave B). LegacyCarouselAcl = single CarouselProjectModel↔editorial translator; writes via the AE-0107 owner (co-located in editorial infra); lock_version+checkpoints preserved. 22 editorial tests, 720 carousel-suite pass, mypy 476, integrity 0 blockers.

## Files Touched

modules/editorial/infrastructure/legacy_carousel_acl.py (new), modules/editorial/infrastructure/carousel_project_write_owner.py (AE-0107 owner relocated here), modules/editorial/{bootstrap,public,__init__}.py, modules/editorial/infrastructure/__init__.py, tests/unit/modules/editorial/test_legacy_carousel_acl.py

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
