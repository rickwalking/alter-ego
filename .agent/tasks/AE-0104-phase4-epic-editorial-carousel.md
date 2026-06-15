# AE-0104 — Phase 4 epic: EditorialProject facade over CarouselProject

Status: Review
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: N/A (epic; sub-tickets carry branches)
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Introduce an `editorial` bounded context (EditorialProject/EditorialWorkflow + status language) behind a public facade, with a legacy carousel ACL as the single translator between `carousel_projects` persistence and editorial concepts; route workflow start/state/resume through editorial handlers; move source material/assignments/review/optimistic-locking behind ports; separate approval from public release. Tracks AE-0105..0113.

## Problem

The carousel workflow logic is the `CarouselProject` god object — five writers of the `carousel_projects` row, workflow logic in routes + ~73 services, no module boundary. Phase 4 carves the workflow slice into `modules/editorial/` behind a facade, behavior-preserving.

## Scope

- Track and integrate children AE-0105 (field-ownership map), AE-0106 (safety net), AE-0107 (single write owner), AE-0108 (editorial skeleton), AE-0109 (legacy ACL), AE-0110 (workflow routes behind handlers), AE-0111 (ports + approval≠release), AE-0112 (import contracts + exit gate).
- Own ONLY the workflow slice (editorial_workflow* routes/services + workflow-owned carousel_projects fields + checkpoints). Presentation/CRUD/media/publishing/strategies/creator-assets stay (Phase 5+).
- Enforce the epic exit gate below before closing.
- Phase 2.5 was skipped: its scaled-down contingent exit-gate items (DB restore drill + trace-correlated smoke) are delivered here as AE-0113; the full-track items (three-entry-point authz contract tests) are AE-0113 per ADR-0009 lines 108-117.

## Non-Goals

- No carousel presentation/CRUD/media extraction (Phase 5+).
- No renames; no new Unit of Work; no agent/workflow behavior change.
- No schema-modifying migration unless forced (then the checkpoint-drain rule applies).

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] THE epic SHALL be Done only when AE-0105..0113 are all Done/merged
- [ ] THE existing carousel workflow API + SSE behavior SHALL remain byte-identical (AE-0106 snapshots diff=0)
- [ ] Editorial handlers SHALL NOT import carousel ORM models directly; the legacy ACL SHALL be the only legacy-persistence translator
- [ ] THE LangGraph checkpoint identifiers + schemas + `lock_version` semantics SHALL be unchanged
- [ ] THE ADR-0009 Phase-4 deferred evidence (three-entry-point authorization contract tests + scaled-down rollback drill, AE-0113) SHALL be complete BEFORE any carousel write path is redirected (AE-0107)
- [ ] WHEN any schema-modifying migration is introduced THE checkpoint-drain rule SHALL be satisfied first (no migration while a checkpoint references the old shape)
- [ ] THE editorial-application-isolation + editorial-public-facade import contracts SHALL be KEPT and the AE-0082 baseline ratcheted down or held; gates.sh + check-integrity green

## Gherkin Scenarios

Not applicable — epic tracker; behavior verified by child tickets (esp. the AE-0106 safety net).

## Delta

### ADDED

- docs/plans/phase-4-editorial-carousel.md (this epic)

### MODIFIED

- `.agent/` board state as children progress

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: —
- Blocked by: None (tracks AE-0105-0112)
- Related: AE-0103, AE-0081, ADR-0009 (lines 108-117)

## Implementation Plan

1. Wave A: AE-0105, AE-0106, AE-0108.
2. Wave B: AE-0107, AE-0109.
3. Wave C: AE-0110 (gate on AE-0041/0044/0045/0046 merge).
4. Wave D: AE-0111.
5. Wave E: AE-0112.

Epic complete — all children AE-0105..0113 implemented, QA-PASSED (2 rounds/wave), in Review. Editorial workflow slice extracted behind facade + ACL; byte-identical (safety net 19/19); single write owner + Mapped[] typing (no overrides); exit gate CI-enforced (16 import contracts, baseline ratcheted api->infra 98→81, get_container 26→14); ADR-0009 deferred evidence (AE-0113) delivered. Awaiting Phase 4 PR merge.

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
