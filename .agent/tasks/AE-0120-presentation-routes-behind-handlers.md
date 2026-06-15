# AE-0120 — Presentation routes behind presentation handlers via facade (byte-identical)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0120-presentation-routes
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move the presentation endpoints (media: pdf/blog/design/images/slide-images/slides/download; preview; strategies; admin design-tokens/render-slides; creator-assets) behind presentation application handlers via the facade; routes become thin adapters. Response schemas + FileResponse bytes/headers + artifact URLs byte-identical.

## Problem

Presentation routes construct services/repos directly and read/write the carousel row + files. They must delegate to the AE-0117 facade + AE-0118 ACL with no behavior change.

## Scope

- Each presentation endpoint delegates to a presentation handler via the facade, resolved by a get_presentation_service edge DI provider (mirror api/dependencies/editorial.py); routes import no carousel/slide ORM and no get_container; writes via the platform UoW + the AE-0118 owner.
- Preserve the response schemas, FileResponse content-type/headers/bytes, artifact URL strings, status codes, and access checks (resource_access/creator-asset) EXACTLY.
- Presentation application code imports no concrete Postgres repo (port/facade only).
- THE crud.py project-GET design-token merge (merge_design_tokens_with_disk, response-only) is handled per the AE-0115 classification — either left as a documented deferred read or delegated to the presentation facade (no behavior change either way).

## Non-Goals

- No artifact-build/export port wiring yet (AE-0121).
- No distribution/publish route change.
- No schema/contract change.

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] EACH presentation endpoint (media/preview/slides/strategies/design/admin/creator-assets) SHALL delegate via the presentation facade + handlers (thin adapter routes)
- [ ] WHEN a presentation endpoint is called THE response (JSON schema OR FileResponse content-type/headers/bytes) + artifact URLs SHALL diff to ZERO against the AE-0116 snapshots
- [ ] THE presentation routes SHALL NOT import the carousel/slide ORM or get_container; presentation application imports no concrete Postgres repo
- [ ] Presentation write endpoints (design-token refresh, render-slides, creator-asset, strategy apply) SHALL persist via the platform UoW (the AE-0118 owner); routes SHALL NOT call db.commit() directly
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass; AE-0116 safety net green

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0116 safety net (diff=0).

## Delta

### ADDED

- presentation command/query handlers
- api/dependencies/presentation.py edge provider

### MODIFIED

- api/routes/carousels/{media,preview,strategies,admin,creator_assets}.py (thin adapters via facade)

### REMOVED

- Direct service/repo construction + carousel/slide ORM access in the presentation routes

## Affected Areas

- Backend: presentation module
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: presentation routes
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0121, AE-0122
- Blocked by: AE-0116, AE-0117, AE-0118, AE-0119
- Related: AE-0110, AE-0045, AE-0046, AE-0114

## Implementation Plan

1. Add get_presentation_service edge provider.
2. Move media/preview/strategies/admin/creator-asset logic into presentation handlers via the ACL/owner.
3. Verify FileResponse bytes + schemas + URLs diff=0. GATE: AE-0045/0046 merged first.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave C). media/preview/strategies/admin/creator-asset routes → PresentationHandlers via facade + api/dependencies/presentation.py edge provider; byte-identical (AE-0116 21/21 incl. FileResponse digests); no route ORM/commit; mypy 496, lint-imports 16/0, api->infra ratcheted 81→79, check-integrity 0 blockers, 763 regression tests pass.

## Files Touched

api/routes/carousels/{media,preview,strategies,admin,creator_assets,crud}.py, api/dependencies/presentation.py (new), modules/presentation/application/handlers.py (new), modules/presentation/{bootstrap,public,__init__,infrastructure/presentation_acl}.py, tests/unit/api/test_preview_carousel_image.py

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
