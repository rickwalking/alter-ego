# AE-0129 — Distribution behind ports (captions/Instagram/LinkedIn channel-delivery) — behavior-preserving

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0129-publishing-distribution
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move distribution (caption/Instagram/LinkedIn generation + channel delivery) behind publishing distribution ports; the Meta/Instagram + LinkedIn publishers become channel adapters implementing the ports. Behavior-preserving; no live keys in tests.

## Problem

Distribution (captions, Instagram publish, LinkedIn) is scattered across carousel routes/services with embedded columns. Publishing should own distribution behind a DistributionPublisher port; vendor/channel SDKs become adapters.

## Scope

- Define a DistributionPublisher / channel port (caption + Instagram + LinkedIn); the Meta Instagram publisher + LinkedIn generator become adapters implementing it (vendor SDK imports in the adapter/infrastructure layer).
- Route publishing.py (publish-instagram, generate-caption) through the publishing facade + the distribution port; reads of caption/linkedin go through the publishing facade.
- Behavior-preserving: identical channel payloads, preconditions, response shapes; deterministic stubs in tests (no live Meta/LLM key).

## Non-Goals

- No new channels/SEO behavior (no SEO optimizer exists today; out of scope).
- No embedded-column drop.
- No distribution-payload change.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] A DistributionPublisher/channel port SHALL be defined; Instagram + LinkedIn publishers SHALL implement it as adapters (vendor SDK in the adapter layer)
- [ ] publish-instagram + generate-caption SHALL route through the publishing facade + the distribution port with identical channel payloads/preconditions/shapes
- [ ] Publishing application/domain SHALL depend only on the port (no direct channel SDK import)
- [ ] WHEN the AE-0125 safety net + a deterministic-stub channel suite run THEY SHALL pass (diff=0; no live key)
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass with no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; verified by the AE-0125 safety net + channel adapter tests.

## Delta

### ADDED

- DistributionPublisher/channel port + Instagram/LinkedIn adapters + deterministic stub tests

### MODIFIED

- api/routes/carousels/publishing.py via facade; distribution services behind the port

### REMOVED

- Direct channel-SDK coupling in publishing application

## Affected Areas

- Backend: publishing module
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: publishing/blog/read routes
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0132
- Blocked by: AE-0125, AE-0126
- Related: AE-0119, AE-0123

## Implementation Plan

1. Define the channel port.
2. Make Instagram/LinkedIn implement it (adapters).
3. Route publishing.py via the facade; stub-channel tests; safety net diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 6 breakdown).

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
