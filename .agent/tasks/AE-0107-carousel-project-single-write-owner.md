# AE-0107 — legacy.carousel_project single write owner for workflow-owned fields

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0107-carousel-single-writer
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Make a single owner the sole writer of the workflow-owned `carousel_projects` fields (status/phase/workflow_status/lock_version + workflow content syncs), routing the scattered writers (routes + artifact/resume services) through it. Behavior-preserving; commits via the platform UoW.

## Problem

Five places write carousel_projects today; independent module write ownership (and the AE-0109 ACL) require a single writer for the workflow-owned fields first (per AE-0105 map). Direct route/service mutations + multiple commits violate the single-committer rule.

## Scope

- Per the AE-0105 map, route ALL writes to the workflow-owned fields (status, current_phase, phase_status, workflow_status, lock_version, workflow content syncs) through one owner (the editorial workflow service / a legacy single-writer adapter).
- Preserve the `lock_version` optimistic-lock bump on resume EXACTLY (concurrent-resume test stays green).
- Writes commit via the platform UoW (single committer); routes/artifact services stop calling `db.commit()` for workflow-owned fields directly.
- Presentation/CRUD writers (documented deferred in AE-0105) are left unchanged.

## Non-Goals

- No editorial module yet (AE-0108/0110).
- No change to presentation/CRUD writers.
- No schema change; no lock-semantics change.
- OUT OF SCOPE (deferred, per the AE-0105 map): the atomic terminal-finalization write (`editorial_finalize` → `repo.update_project`, which persists the WO fields status/error_message TOGETHER with the deferred Phase-5 presentation columns design_tokens/pdf_path/artifact_version in ONE commit) and the generic `CarouselRepository.update_project` (W1, `update_from_entity`) remain on the legacy full-entity persistence path — splitting their WO-field writes out would break the single-commit atomicity (byte-identical). AE-0107 owns the workflow-PHASE writes (sync_phase, assign_reviewer, set_phase_status, resume lock CAS).

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] ALL writes to the workflow-owned carousel_projects fields SHALL go through the single owner (no direct route/artifact-service model mutation of those fields)
- [ ] THE `lock_version` optimistic-lock bump on resume SHALL be preserved exactly (concurrent-resume behavior unchanged)
- [ ] Workflow-owned writes SHALL commit via the platform UoW; the affected routes/services SHALL NOT call `db.commit()`/`session.commit()` for those fields directly
- [ ] WHEN the AE-0106 safety net runs THE workflow API + SSE responses SHALL diff to ZERO
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass with no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0106 safety net.

## Delta

### ADDED

- legacy single-writer owner/adapter for workflow-owned carousel_projects fields

### MODIFIED

- api/routes/carousels/editorial_workflow.py, application/services/carousel/editorial_workflow_service.py + resume_runner + artifact_build_service (route writes through the owner)

### REMOVED

- Direct workflow-field model mutations + commits scattered across routes/services

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
- Blocked by: AE-0105, AE-0106, AE-0113
- Related: AE-0104, ADR-0009

## Implementation Plan

1. Use AE-0105 map to enumerate workflow-owned fields + writers.
2. Introduce the single owner; route writers through it via UoW.
3. Preserve lock_version bump; verify safety net diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

Dev Complete (Wave B). CarouselProjectWriteOwner consolidates all workflow-owned writes; AE-0106 diff=0; lock_version dual-CAS preserved; .importlinter net-neutral regen. 689 carousel/workflow tests pass; gate spine 14 PASS/0 FAIL/3 SKIP; integrity 0 blockers.

## Files Touched

modules/editorial/infrastructure/carousel_project_write_owner.py (relocated from application — resolves DDD blocker), infrastructure/database/models/carousel.py (9 WO columns → Mapped[]), editorial_workflow_service.py, editorial_workflow_resume_runner.py, api/routes/carousels/editorial_workflow.py, editorial_workflow_routes_validate.py, backend/.importlinter (net-neutral regen)

## Test Evidence

Pending.

## QA Report

Phase 4 Wave B batch QA — round 1 surfaced the finalize/W1 atomic-terminal-write boundary (documented deferral, byte-identical-justified); round 2 PASS (0 critical/warning/minor). See `.agent/reports/phase-4-wave-b.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
