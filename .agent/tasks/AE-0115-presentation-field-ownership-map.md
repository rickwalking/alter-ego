# AE-0115 — Presentation field/surface ownership map (extends AE-0105)

Status: Dev Complete
Tier: T2
Priority: High
Type: Docs
Area: Docs/Arch
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0115-presentation-ownership-map
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Author docs/architecture/presentation-surface-ownership.md (extending the AE-0105 carousel field map): map the presentation carousel_projects columns + the CarouselSlideModel rows to writers (file:line), classify presentation-owned vs deferred (distribution/Phase 6), document the artifact_version↔lock_version CAS pairing, and map the editorial↔presentation call boundary (design/images/export nodes + finalize artifact build + the phase_progress callback).

## Problem

Phase 5 redirects presentation reads/writes and moves the design/image/export operations behind a port; without a precise surface map (which columns, which slide writes, the CAS pairing, the editorial coupling points) AE-0118/0120/0121 cannot be scoped safely.

## Scope

- Map every PRESENTATION carousel_projects column (design_tokens/output_dir/pdf_path*/artifact_version/slide_layout_strategy/presentation_policy_*/title*/colors/creator_*) + the CarouselSlideModel columns to writer(s) file:line and presentation-owned vs deferred (distribution).
- Document the artifact_version↔lock_version compare-and-swap pairing (carousel_artifact_build_repository.activate_build) and its shared use with the editorial AE-0107 resume CAS — the constraint AE-0118/0121 must preserve.
- Map the editorial→presentation coupling points: editorial_finalize artifact build call, the design/images/export workflow nodes, and the nodes/images.py phase_progress write (the presentation→editorial callback boundary).
- Confirm the distribution columns (blog/caption/linkedin) are OUT of Phase 5 (Phase 6) and the publish/is_public path stays.
- Document the SHARED lock_version owner hierarchy: the editorial AE-0107 CarouselProjectWriteOwner (resume CAS) and the presentation artifact activate_build CAS both bump lock_version — specify how the presentation owner coordinates (single shared CAS primitive / serialization) so AE-0118 can implement + test it without clobber.
- Classify the crud.py project GET presentation read (merge_design_tokens_with_disk, response-only merge): presentation-owned read — either deferred-with-rationale or served via the presentation facade in AE-0120.

## Non-Goals

- No code/schema change (docs only).
- No distribution/publishing mapping beyond marking them deferred.

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] THE document SHALL map every presentation carousel_projects column + CarouselSlideModel column with type, writer(s) file:line, and presentation-owned vs deferred classification
- [ ] THE document SHALL document the artifact_version↔lock_version CAS pairing and the constraint that AE-0118/0121 preserve it exactly
- [ ] THE document SHALL map the editorial↔presentation call boundary (finalize artifact build, design/images/export nodes, phase_progress callback) as the port surface
- [ ] THE document SHALL flag every presentation column/slide field written by more than one writer (consolidation edge cases)
- [ ] WHEN AE-0118/0120/0121 are planned THE map SHALL be sufficient to scope the presentation ACL + the editorial→presentation port (no unmapped surface)

## Gherkin Scenarios

Not applicable — documentation deliverable; correctness verified by AE-0118/0120/0121 referencing it.

## Delta

### ADDED

- docs/architecture/presentation-surface-ownership.md

### MODIFIED

- docs/plans/phase-5-presentation.md (link the artifact)

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none
- Tests: contract/behavior tests
- Docs: presentation surface map
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0118, AE-0120, AE-0121
- Blocked by: None
- Related: AE-0105, AE-0114

## Implementation Plan

1. Inventory presentation columns + slide model from the ORM + AE-0105.
2. Trace writers + the artifact_version/lock_version CAS.
3. Map the editorial↔presentation coupling; classify owned vs deferred.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave A). Authored docs/architecture/presentation-surface-ownership.md — 23 presentation carousel_projects columns + 13 slide columns mapped (writers file:line, owned vs deferred); artifact_version↔lock_version compound CAS pairing + shared-owner coordination documented (§3); editorial↔presentation call boundary (finalize artifact build, design/images/export nodes, phase_progress callback) mapped (§5); 14 multi-writer fields flagged; crud GET design-token merge classified as facade-served (AE-0120); distribution + is_public confirmed OUT (Phase 6). Wave A: 21+11 tests pass; mypy 491, integrity 0 blockers, no suppressions.

## Files Touched

docs/architecture/presentation-surface-ownership.md

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
