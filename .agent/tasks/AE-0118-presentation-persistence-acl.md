# AE-0118 — Presentation persistence: single writer/ACL for presentation columns + slide rows (preserve artifact_version↔lock_version CAS)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0118-presentation-persistence
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Make the presentation module the owner of writes to the presentation carousel_projects columns + slide rows, via a presentation ACL/single-writer in modules/presentation/infrastructure (mirroring the editorial ACL/owner). Preserve the artifact_version↔lock_version activation CAS EXACTLY, coordinating with the AE-0107 CarouselProjectWriteOwner.

## Problem

Presentation columns (design_tokens/pdf_path*/artifact_version/output_dir/policy/colors/title/creator) + slide rows are written by scattered services/routes. Independent presentation ownership requires a single writer/ACL first (per the AE-0115 map), without breaking the artifact_version↔lock_version CAS shared with editorial.

## Scope

- Implement a presentation ACL/single-writer (modules/presentation/infrastructure) — the ONLY presentation code importing the carousel/slide ORM — that reads/writes the presentation columns + slide rows; route the scattered presentation writers through it; commit via the platform UoW.
- Preserve the artifact_version↔lock_version compare-and-swap in carousel_artifact_build_repository.activate_build EXACTLY; coordinate with the editorial AE-0107 owner so the shared lock_version token is not clobbered (the pairing stays atomic).
- Editorial/global callers reach presentation persistence via the presentation public facade (no presentation-internal imports).
- Add ACL/owner + slide-write contract tests; keep AE-0116 diff=0.

## Non-Goals

- No routes moved (AE-0120).
- No distribution columns.
- No schema change; no lock-semantics change.
- No second persistence translator.

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] THE presentation ACL/single-writer SHALL be the ONLY presentation code importing the carousel/slide ORM; presentation application/domain import no ORM
- [ ] ALL writes to the presentation columns + slide rows SHALL go through the presentation owner (no scattered direct ORM mutation of those); writes commit via the platform UoW
- [ ] THE artifact_version↔lock_version activation CAS SHALL be preserved exactly (pairing atomic; coordinated with the AE-0107 owner; concurrent behavior unchanged)
- [ ] WHEN the AE-0116 safety net runs THE presentation responses + artifact URLs + FileResponse bytes SHALL diff to ZERO
- [ ] A concurrency test SHALL assert that a presentation artifact activate_build and an editorial resume lock bump run against the shared lock_version WITHOUT clobbering each other (the artifact_version↔lock_version pairing stays atomic; serialized through the coordinated owners)
- [ ] THE presentation ACL/owner contract tests SHALL assert authorization parity on the presentation WRITE entry points (HTTP at minimum: design-token refresh, render-slides, creator-asset, strategy apply) — extending the ADR-0009 write-path evidence (AE-0113 covered the workflow paths; no new epic evidence ticket needed)
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass with no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0116 safety net + CAS/contract tests.

## Delta

### ADDED

- modules/presentation/infrastructure presentation ACL/single-writer (+ tests)

### MODIFIED

- scattered presentation writers routed through the owner (design token refresh, artifact build pdf paths, slide writes)

### REMOVED

- Direct presentation-column/slide ORM mutations scattered across services/routes

## Affected Areas

- Backend: presentation module
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none yet
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0120, AE-0121
- Blocked by: AE-0115, AE-0116, AE-0117
- Related: AE-0107, AE-0109, AE-0114

## Implementation Plan

1. Use the AE-0115 map to enumerate presentation writers + the CAS.
2. Implement the presentation ACL/owner; route writers through it via UoW.
3. Preserve artifact_version↔lock_version CAS (coordinate with AE-0107); verify safety net diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave B). PresentationWriteOwner + PresentationPersistenceAcl (sole presentation ORM importers); admin refresh routed through the owner; artifact_version↔lock_version CAS preserved + no-clobber tested; write-path authz parity (extends AE-0113). Editorial-invoked writers deferred to AE-0121's port (documented). mypy 493, lint-imports 16/0, check-integrity 0 blockers, 919 regression tests pass.

## Files Touched

modules/presentation/infrastructure/{presentation_acl,presentation_write_owner}.py (new), modules/presentation/{public,infrastructure/__init__}.py, api/routes/carousels/admin.py, tests/unit/modules/presentation/test_presentation_write_owner.py, tests/integration/test_presentation_write_path_authz.py, tests/features/presentation_persistence_acl.feature

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
