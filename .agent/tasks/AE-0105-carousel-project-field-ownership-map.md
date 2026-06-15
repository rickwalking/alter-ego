# AE-0105 — carousel-project-field-ownership.md — column/invariant/owner/concurrency map

Status: Ready
Tier: T2
Priority: High
Type: Docs
Area: Docs/Arch
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0105-carousel-field-ownership
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Author `docs/architecture/carousel-project-field-ownership.md` mapping every `carousel_projects` column to its invariant, command owner (which future module/context writes it), and concurrency token. This is the roadmap-mandated prerequisite for any editorial write redirection (folded-in Phase 2.5 deliverable).

## Problem

`carousel_projects` is a ~40-column god row with five distinct writers and no documented ownership. Without a field-ownership map, AE-0107's single-writer consolidation and AE-0109's ACL cannot be scoped safely.

## Scope

- Map EVERY carousel_projects column: name, type, invariant/meaning, current writer(s) (file:line), the owning context (editorial vs presentation vs distribution vs CRUD), and concurrency token (`lock_version`).
- Enumerate the current writers (carousel_repository, crud.py, admin.py, editorial_workflow routes, editorial_workflow_service + resume_runner + artifact_build_service) and classify each write as workflow-owned (Phase 4) vs deferred (Phase 5+).
- Record the consistency relationship between the legacy row and the future editorial module (single-writer rule + retained-process-manager note).

## Non-Goals

- No code change (docs only).
- No schema change.
- No relocation of presentation/distribution columns (documented as deferred only).

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] THE document SHALL list every carousel_projects column with type, invariant, current writer(s) (file:line), owning context, and concurrency token
- [ ] THE document SHALL classify each writer as workflow-owned (Phase 4 / AE-0107) or deferred (Phase 5+) with rationale
- [ ] THE document SHALL name `lock_version` as the optimistic-lock concurrency token and where it is bumped
- [ ] THE document SHALL state the single-write-owner rule and the legacy-row↔editorial consistency relationship
- [ ] WHEN AE-0107 and AE-0109 are planned THE map SHALL be sufficient to scope which fields move behind editorial ports (no unmapped column)

## Gherkin Scenarios

Not applicable — documentation deliverable; correctness verified by AE-0107/0109 referencing it.

## Delta

### ADDED

- docs/architecture/carousel-project-field-ownership.md

### MODIFIED

- docs/plans/phase-4-editorial-carousel.md (link the artifact)

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none
- Tests: contract/behavior tests
- Docs: field-ownership map
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0107, AE-0109
- Blocked by: None
- Related: AE-0104, ADR-0009

## Implementation Plan

1. Inventory carousel_projects columns from the ORM model.
2. Trace every writer (grep .add/.commit/update_from_entity/field mutation).
3. Classify owner + concurrency; write the map.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

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
