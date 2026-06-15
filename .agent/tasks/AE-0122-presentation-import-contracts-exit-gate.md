# AE-0122 — Presentation import contracts + exit gate + baseline ratchet + docs

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0122-presentation-import-contracts
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add Import Linter contracts enforcing the presentation exit gate (presentation application/domain isolated from frameworks/container/infrastructure except the presentation ACL; public-facade; presentation imports no editorial internals), ratchet the AE-0082 baseline down, and document presentation as a worked example. Mirrors AE-0103/AE-0112.

## Problem

The presentation boundary must be CI-enforced (building on AE-0095/0103/0112), the editorial→presentation direction locked, or the carousel coupling will silently return.

## Scope

- Add contracts via render_importlinter: presentation-application-isolation (application/domain forbidden from importing frameworks/get_container/infrastructure — carousel/slide ORM only via the presentation ACL) + presentation-public-facade (cross-module callers use the facade only). Name the presentation ACL as the only allowed carousel-ORM path.
- Add a contract/assertion that presentation does NOT import editorial internals (dependency direction editorial→presentation).
- Regenerate .importlinter; ratchet the AE-0082 baseline DOWN (api->infra / get_container) or hold; --check stays PASS; demonstrate+revert a violation.
- Update module-conventions.md §12 with presentation as a worked example; re-affirm the checkpoint-drain rule.

## Non-Goals

- No weakening of existing contracts.
- No behavior change (CI/docs only).

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] Import Linter contracts SHALL isolate presentation.application/domain (no frameworks/get_container/infrastructure; carousel/slide ORM only via the presentation ACL) and enforce the public facade; lint-imports KEEPS them
- [ ] THE presentation-application-isolation contract SHALL name `modules.presentation.infrastructure.<presentation_acl_module>` as the ONLY allowed carousel/slide-ORM import path (explicit, documented exception in render_importlinter — parity with AE-0112's legacy_carousel_acl naming)
- [ ] A contract/assertion SHALL enforce that presentation imports no editorial internals (editorial→presentation direction)
- [ ] WHEN new code violates either boundary THE contract SHALL fail (demonstrated, reverted)
- [ ] THE AE-0082 baseline/--check SHALL ratchet DOWN or hold and stay PASS
- [ ] module-conventions.md SHALL document presentation as a worked example (§12) + re-affirm the checkpoint-drain rule; gates.sh + check-integrity + full suite green

## Gherkin Scenarios

Not applicable — CI/docs deliverable; falsifiability demonstrated by a reverted violation.

## Delta

### ADDED

- presentation contracts in scripts/metrics/import_baseline.py (render_importlinter); module-conventions.md §12

### MODIFIED

- backend/.importlinter (regenerated); scripts/metrics/import_baseline.py (baseline constants)

### REMOVED

- None

## Affected Areas

- Backend: presentation module
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none yet
- Tests: contract/behavior tests
- Docs: module-conventions §12
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0114 (closes epic)
- Blocked by: AE-0120, AE-0121
- Related: AE-0103, AE-0112, AE-0114

## Implementation Plan

1. Add the presentation contracts to render_importlinter; regenerate .importlinter.
2. Ratchet baseline; demonstrate+revert a violation.
3. Document §12 + re-affirm checkpoint-drain.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave E). 3 presentation contracts (isolation/public-facade/no-editorial; zero ignores; violations demonstrated+reverted); baseline ratcheted api->infra 81→79 + agents->application 20→19; module-conventions §12. lint-imports 19/0, --check PASS, mypy 499, integrity 0 blockers.

## Files Touched

scripts/metrics/import_baseline.py (presentation contracts + acyclic no-editorial contract + baseline api->infra 81→79/agents->application 20→19), backend/.importlinter (regenerated, 19 contracts), docs/architecture/module-conventions.md (§12)

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
