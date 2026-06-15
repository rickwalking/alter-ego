# AE-0111 — Source/assignments/review/optimistic-locking behind editorial ports; split approval from public release

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0111-editorial-ports-approval-release
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move source material, assignments, review decisions, and optimistic locking behind editorial ports (consumed via the facade/ACL), and separate approval from public release at the contract level (approving content ≠ making it public). Behavior-preserving.

## Problem

Source/assignments/review/locking logic is still coupled to carousel services + the ORM; and approval and public release are conflated. The editorial contract must own these as ports with a clear approval≠release boundary.

## Scope

- Define editorial ports for source material, assignments, review decisions, and optimistic locking; back them with adapters over the existing infrastructure via the ACL.
- Separate approval (workflow content approved) from public release (is_public/visibility) at the contract level — distinct operations/states.
- Preserve lock_version semantics + review-action behavior + status transitions EXACTLY (AE-0106 diff=0).
- Editorial application code depends on the ports only (no concrete repo / carousel ORM).

## Non-Goals

- No visibility/permission behavior change (only the contract split).
- No schema change.
- No presentation extraction.

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] Source material, assignments, review decisions, and optimistic locking SHALL be accessed via editorial ports (editorial application imports no concrete repo / carousel ORM)
- [ ] Approval SHALL be separated from public release at the contract level (distinct operations/states; approving ≠ making public)
- [ ] THE `lock_version` optimistic-lock + review-action + status-transition behavior SHALL be preserved exactly
- [ ] WHEN the AE-0106 safety net runs THE workflow API + SSE SHALL diff to ZERO
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass with no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0106 safety net.

## Delta

### ADDED

- editorial ports (source/assignments/review/locking) + adapters; approval vs release contract operations

### MODIFIED

- modules/editorial/application + infrastructure (ports/adapters); editorial handlers

### REMOVED

- Direct carousel-service/ORM coupling for source/assignments/review/locking in editorial code

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

- Blocks: AE-0112
- Blocked by: AE-0110
- Related: AE-0104, ADR-0009

## Implementation Plan

1. Define the four ports + adapters via the ACL.
2. Split approval from release at the contract level.
3. Preserve lock_version + transitions; safety net diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

Dev Complete (Wave D). 6 editorial ports + adapters (source/assignments/review/locking + approval/release); approval≠release contract split; lock_version preserved; editorial app imports no carousel ORM. mypy 480, lint-imports 14/0, safety net 19/19, check-integrity 0 blockers, 801 regression tests pass.

## Files Touched

modules/editorial/domain/{ports,release}.py, modules/editorial/infrastructure/editorial_port_adapters.py (new), modules/editorial/application/service.py, modules/editorial/{bootstrap,public,__init__}.py, tests/unit/modules/editorial/test_editorial_ports.py

## Test Evidence

Pending.

## QA Report

Phase 4 Wave D QA — converged PASS in 2 independent rounds (0 findings). See `.agent/reports/phase-4-wave-d.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
