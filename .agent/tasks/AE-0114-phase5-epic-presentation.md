# AE-0114 — Phase 5 epic: Extract Carousel Presentation

Status: Ready
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

Extract a `presentation` bounded context (slides, design/theming, layout strategies, policy+validation, rendering, image generation + providers, artifact build/activation, export, creator assets) behind a public facade; the editorial workflow invokes presentation through a port/facade. Tracks AE-0115..0122.

## Problem

The carousel presentation logic (~30 services + 5 route files + slide ORM + presentation columns) is still inside the global carousel surface. Phase 5 carves it into modules/presentation behind a facade + ACL, behavior-preserving, so carousel means presentation only.

## Scope

- Track + integrate children AE-0115 (field map), AE-0116 (safety net), AE-0117 (skeleton), AE-0118 (persistence/ACL), AE-0119 (image-provider ports), AE-0120 (routes behind handlers), AE-0121 (artifact/export/design behind contracts + editorial→presentation port), AE-0122 (import contracts + exit gate).
- Own PRESENTATION only: slides + the presentation carousel_projects columns (design_tokens/output_dir/pdf_path*/artifact_version/slide_layout_strategy/presentation_policy_*/title*/colors/creator_*); design/render/image/artifact/export/creator-assets.
- Enforce the epic exit gate below before closing.

## Non-Goals

- No blog/distribution extraction (caption/linkedin/blog → Phase 6); no publishing/is_public; no persona; no workflow-state ownership (editorial).
- No renames; no new Unit of Work; no agent/provider behavior change; no schema migration (checkpoint-drain rule if forced).

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] THE epic SHALL be Done only when AE-0115..0122 are all Done/merged
- [ ] Carousel SHALL mean presentation only (the presentation module owns slides/design/render/artifact/export)
- [ ] THE editorial workflow SHALL invoke presentation only through a port/public facade (no presentation-internal calls)
- [ ] Presentation SHALL NOT own blog, publishing, persona, or workflow state
- [ ] Presentation response schemas + artifact URLs + FileResponse bytes SHALL be byte-identical (AE-0116 diff=0); artifact_version↔lock_version CAS + checkpoints preserved
- [ ] THE presentation-application-isolation + presentation-public-facade contracts SHALL be KEPT and the AE-0082 baseline ratcheted down or held; gates.sh + check-integrity green

## Gherkin Scenarios

Not applicable — epic tracker; behavior verified by child tickets (esp. the AE-0116 safety net).

## Delta

### ADDED

- docs/plans/phase-5-presentation.md (this epic)

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
- Blocked by: None (tracks AE-0115-0122)
- Related: AE-0104, AE-0112, AE-0081, ADR-0009

## Implementation Plan

1. Wave A: AE-0115, AE-0116, AE-0117.
2. Wave B: AE-0118, AE-0119.
3. Wave C: AE-0120 (gate on AE-0045/0046 merge).
4. Wave D: AE-0121.
5. Wave E: AE-0122.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

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
