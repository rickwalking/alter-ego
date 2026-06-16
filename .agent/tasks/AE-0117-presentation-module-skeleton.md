# AE-0117 — modules/presentation skeleton + facade + domain + re-exported ports

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0117-presentation-module
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Create modules/presentation/ (domain/application/infrastructure/api + public.py + bootstrap.py + constants.py) mirroring modules/editorial; define presentation domain (PresentationProject view, DesignPolicy, SlideView, presentation policy types) + re-export CarouselSlide/CarouselRepository ports via object-identity shims. No routes moved yet.

## Problem

There is no presentation module today; the skeleton + domain + facade must exist before the ACL/persistence (AE-0118), provider ports (AE-0119), and route delegation (AE-0120).

## Scope

- Scaffold modules/presentation per conventions + the editorial pattern (public.py facade + bootstrap.py manual DI, no get_container).
- Define presentation domain entities/value objects (PresentationProject view over the carousel row's presentation fields, DesignPolicy/SlideView) + re-export the presentation policy types (presentation_policy_types) and CarouselSlide entity/SlideValidation models via object-identity shims.
- Re-export the CarouselRepository / slide repository ports so existing callers keep resolving; reuse the platform/database UoW.
- Add an import/type smoke test proving public symbols import + the re-exports are object-identical.

## Non-Goals

- No routes/ACL/providers moved (AE-0118/0119/0120).
- No render/image behavior change.
- No distribution.

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] modules/presentation SHALL exist per conventions with public.py facade + bootstrap.py (manual DI, no get_container)
- [ ] Presentation domain entities/value objects + policy types SHALL be typed (no Any) and re-export existing presentation/slide types via object-identity shims (no new domain strings)
- [ ] THE CarouselSlide entity + slide/CarouselRepository ports SHALL be re-exported (existing callers keep resolving; CI-verified)
- [ ] THE module SHALL reuse the platform/database UoW (no new UoW)
- [ ] WHEN mypy/lint-imports/pytest run THEY SHALL pass with no new violations and no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving scaffolding; verified by mypy/lint-imports + the AE-0116 safety net.

## Delta

### ADDED

- modules/presentation/{domain,application,infrastructure,api}/, public.py, bootstrap.py, constants.py
- presentation domain entities/value objects + policy-type re-exports
- tests/unit/modules/presentation/*

### MODIFIED

- None (canonical defs stay; re-export only)

### REMOVED

- None

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

- Blocks: AE-0118, AE-0119, AE-0120, AE-0122
- Blocked by: None
- Related: AE-0108, AE-0117, AE-0114

## Implementation Plan

1. Scaffold modules/presentation from the editorial pattern.
2. Define domain + re-export policy/slide types.
3. Re-export ports; bootstrap; mypy/lint-imports/smoke test.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave A). modules/presentation skeleton + public.py facade + bootstrap.py (manual DI, no get_container); PresentationProject view/DesignPolicy/SlideView domain + object-identity re-exports of presentation policy types, ContentSlideCopy/SlideValidation, CarouselSlide, CarouselRepository; reuses platform UoW. mypy 491, lint-imports clean, 11 unit tests; object-identity verified. Wave A: 21+11 tests pass; mypy 491, integrity 0 blockers, no suppressions.

## Files Touched

backend/src/rag_backend/modules/presentation/** (+public.py/bootstrap.py/constants.py/domain), tests/unit/modules/presentation/*

## Test Evidence

Pending.

## QA Report

Phase 5 Wave A batch QA — converged PASS in 2 independent rounds (0 findings). See `.agent/reports/phase-5-wave-a.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
