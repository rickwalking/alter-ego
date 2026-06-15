# AE-0121 — Artifact build/export/design behind presentation contracts; editorial→presentation port; ContentFormatProducer

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0121-presentation-contracts-port
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move artifact build/activation, export/rendering, and design behind presentation contracts; make the editorial workflow invoke presentation through a PORT (design/images/export operations + the finalize artifact build); turn the nodes/images.py phase_progress write into a presentation→editorial callback port; add the presentation-specific ContentFormatProducer extension point.

## Problem

Artifact build/export/design are presentation operations still invoked directly by the editorial workflow (finalize + design/images/export nodes), and the image node writes workflow state directly. Phase 5 puts these behind presentation contracts with a clean editorial→presentation dependency direction.

## Scope

- Define presentation ports for artifact build/activation, export/rendering, and design; the editorial workflow (finalize + the design/images/export nodes) invokes them via the presentation public facade — dependency direction editorial→presentation only (presentation imports no editorial internals).
- Replace the nodes/images.py direct phase_progress write with a presentation→editorial callback port (presentation reports progress; editorial owns workflow state).
- Add the ContentFormatProducer Protocol (format_name + async produce(ProduceFormat) -> ProducedArtifact) as a PRESENTATION-SPECIFIC boundary — do NOT build a generic format framework (only carousel today).
- Move the presentation POLICY/VALIDATION/REVIEW services (presentation_policy*, presentation_review*, presentation_validation*, visible_copy_sanitize, presentation_review_edits) behind presentation contracts, and repoint carousel_workflow_nodes (which imports presentation_review_edits) to call them via the editorial→presentation port — so the exit gate 'carousel = presentation only' holds for every presentation path, not just the design/images/export nodes.
- Preserve the artifact_version↔lock_version CAS + artifact URLs + checkpoints EXACTLY (AE-0116 diff=0).

## Non-Goals

- No generic multi-format framework (single producer until a 2nd format needs it).
- No distribution/publish change.
- No schema migration (checkpoint-drain rule if forced).

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] Artifact build/activation, export/rendering, and design SHALL be behind presentation contracts; the editorial workflow SHALL invoke them only via the presentation public facade (editorial→presentation; presentation imports no editorial internals)
- [ ] THE nodes/images.py phase_progress write SHALL become a presentation→editorial callback port (presentation does not write workflow state directly)
- [ ] A ContentFormatProducer Protocol SHALL be defined as a presentation-specific boundary (no generic format framework)
- [ ] THE artifact_version↔lock_version CAS, artifact URLs, and LangGraph checkpoints SHALL be preserved exactly
- [ ] THE presentation policy/validation/review services SHALL be behind presentation contracts and carousel_workflow_nodes SHALL invoke them via the editorial→presentation port (no direct presentation-internal call from the workflow nodes)
- [ ] WHEN gates.sh + mypy + lint-imports + pytest + the AE-0116 safety net run THEY SHALL pass (diff=0)

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0116 safety net + agent/workflow tests.

## Delta

### ADDED

- presentation artifact/export/design ports + ContentFormatProducer; presentation→editorial progress callback port

### MODIFIED

- editorial_finalize + design/images/export nodes to invoke presentation via the facade; nodes/images.py progress via callback

### REMOVED

- Direct editorial→presentation-internal calls; direct phase_progress write in the image node

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

- Blocks: AE-0122
- Blocked by: AE-0118, AE-0119, AE-0120 (soft-gate: AE-0045/0046 merged — they refactored presentation_review/carousel_presentation; build on them, do not re-refactor)
- Related: AE-0110, AE-0111, AE-0114

## Implementation Plan

1. Define artifact/export/design ports + ContentFormatProducer.
2. Repoint editorial finalize + nodes to the presentation facade; add the progress callback port.
3. Preserve CAS + checkpoints; safety net diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave D). Artifact/export/design + policy/validation/review behind presentation contracts; editorial invokes presentation via facade (acyclic); phase_progress→callback port; ContentFormatProducer; CAS+checkpoints preserved. Both safety nets 40/40 diff=0; mypy 499, lint-imports 16/0, agents->application 20→19, check-integrity 0 blockers, 1126 regression tests pass.

## Files Touched

modules/presentation/domain/{contracts,ports}.py, modules/presentation/infrastructure/editorial_workflow_ports.py (new), modules/presentation/{public,__init__,infrastructure/__init__}.py, application/services/carousel/{editorial_finalize,editorial_visual_pipeline,editorial_progress_reporter}.py, application/services/carousel/nodes/images.py, agents/carousel_workflow_nodes.py, tests (presentation ports + finalize + phase5_parallel)

## Test Evidence

Pending.

## QA Report

Phase 5 Wave D QA — converged PASS in 2 independent rounds (0 findings). See `.agent/reports/phase-5-wave-d.qa.md`.

## Decision Log

Pending.

## Blockers

SOFT GATE (Wave D): AE-0045 (presentation_review Chain-of-Responsibility) + AE-0046 (carousel_presentation
validators) are PASS QA / in Review and touch the same presentation surface this ticket moves — they MUST merge
before the presentation policy/validation/review file movement here, or this ticket owns their current state (no re-refactor).

## Final Summary

Pending.
