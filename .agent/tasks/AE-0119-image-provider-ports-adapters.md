# AE-0119 — Image-provider ports + adapters (registry + OpenAI/Gemini behind ports)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0119-image-provider-ports
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Define presentation ports for image generation (ImageGenerationService / ImageProviderPort + the registry) and convert the concrete vendors (OpenAIImageService, Gemini) into adapters implementing those ports, wired via the presentation module. No image behavior change; no live keys in tests.

## Problem

Image generation couples presentation to concrete vendor SDKs (OpenAI/Gemini) via image_provider_registry. Phase 5 puts the vendors behind ports so presentation application depends on contracts, not SDKs.

## Scope

- Define ImageGenerationService / ImageProviderPort (+ the provider registry contract) in the presentation module; the concrete OpenAIImageService + Gemini service implement the port (adapters in presentation/infrastructure/external or re-exported from the existing locations behind the port).
- Keep the registry resolve(model, style) → provider behavior + the (model,style) combos + prompt-package metadata IDENTICAL.
- Presentation application/domain depend only on the port; vendor SDK imports stay in the adapter/infrastructure layer.
- Add adapter + registry tests with a deterministic fake provider (no live API key).

## Non-Goals

- No new image models/styles.
- No image-output behavior change.
- No generic format framework yet (ContentFormatProducer is AE-0121).

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] AN ImageGenerationService/ImageProviderPort SHALL be defined; OpenAI + Gemini providers SHALL implement it as adapters; vendor SDK imports stay in the adapter/infrastructure layer
- [ ] THE registry resolve(model,style) → provider behavior, the (model,style) combos, and the prompt-package metadata SHALL be unchanged
- [ ] Presentation application/domain SHALL depend only on the port (no direct vendor SDK import)
- [ ] A deterministic fake-provider test suite SHALL cover the registry + adapters (no live API key)
- [ ] WHEN mypy/lint-imports/pytest + the AE-0116 safety net run THEY SHALL pass (diff=0; image paths via the stub)

## Gherkin Scenarios

Not applicable — behavior-preserving port extraction; verified by registry/adapter tests + the AE-0116 safety net.

## Delta

### ADDED

- presentation ImageGenerationService/ImageProviderPort + registry contract; provider adapters; deterministic fake-provider tests

### MODIFIED

- image_provider_registry + nodes/images.py to depend on the port; OpenAI/Gemini services as adapters

### REMOVED

- Direct vendor-SDK coupling in presentation application

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
- Blocked by: AE-0117
- Related: AE-0114, AE-0119

## Implementation Plan

1. Define the port + registry contract.
2. Make OpenAI/Gemini implement it (adapters).
3. Repoint nodes/images.py to the port; fake-provider tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

Dev Complete (Wave B). ImageGenerationService/ImageProviderPort + OpenAI/Gemini adapters (vendor SDK stays in infrastructure); registry behavior unchanged; nodes/images.py typed against the port; 22 fake-provider tests. mypy 494, lint-imports 16/0, check-integrity 0 blockers, 811 regression tests pass; no new suppressions.

## Files Touched

modules/presentation/domain/ports.py, modules/presentation/infrastructure/image_provider_adapters.py (new), modules/presentation/{public,__init__,infrastructure/__init__}.py, application/services/image_provider_registry.py (docstring), application/services/carousel/nodes/images.py (typed to port), tests/unit/modules/presentation/test_image_provider_ports.py

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
