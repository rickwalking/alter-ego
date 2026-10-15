# AE-0373 — Content mode plumbing: pov fields on the project, api and wizard

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Claude (autonomous worker)
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0371-growth-pov-mode
Kanban Card: TBD
Parent: AE-0371
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Persist and expose the content mode and POV inputs on the carousel project (roadmap R2).

## Problem

The project has no notion of mode, thesis, proof, format, slide count, CTA goal or slide-1 photo; the wizard never sends a persona and the backend drops the template strategy.

## Scope

- Additive migration: `carousel_projects` (`content_mode`, `pov_thesis`, `pov_personal_proof`, `pov_format`, `slide_count`, `cta_goal`, `hook_text`, `hook_asset_id`) and `carousel_creator_assets` (`role`, `pose_tag`).
- Domain + ORM mapping; create schema validation; response fields; persona_id and strategy persisted at create.
- Wizard: Modo toggle, tese, prova, formato, nº de slides, objetivo do CTA, persona select, POV formats in the template list; i18n pt/en; component tests.

## Non-Goals

- Generation behaviour (AE-0374/0375/0376).
- Photo picker (AE-0376).

## Acceptance Criteria

- [x] WHEN a create request omits `content_mode` THE SYSTEM SHALL store it as Radar IA (NULL, reported as `news_analysis`).
- [x] WHEN a `pov` create request has a non-blank thesis ≤280 chars, a known format and 8-10 slides THE SYSTEM SHALL persist every POV field and return them.
- [x] WHEN a `pov` create request lacks a thesis, has an unknown format or a slide count outside 8-10 THE API SHALL answer 422.
- [x] WHEN a `news_analysis` request carries POV-only fields THE API SHALL answer 422.
- [x] WHEN a create request carries `persona_id` or `strategy` THE SYSTEM SHALL persist them on the project.
- [x] WHEN the wizard is in POV mode THE UI SHALL require the thesis and show the POV fields and formats; in Radar IA mode it SHALL hide them.

## Gherkin Scenarios

```gherkin
Feature: Carousel content mode

  Scenario: Default mode
    Given a create request without content_mode
    When it is submitted
    Then the project is created with content_mode "news_analysis"

  Scenario: POV project with all fields
    Given a pov create request with a thesis, format "opiniao", 9 slides and cta_goal "send"
    When it is submitted
    Then the response carries the same POV fields

  Scenario: POV without thesis
    Given a pov create request with a blank thesis
    When it is submitted
    Then the API answers 422

  Scenario: POV fields on a Radar IA request
    Given a news_analysis create request with a thesis
    When it is submitted
    Then the API answers 422

  Scenario: Persona and template are persisted
    Given a create request with a persona id and strategy "feature_grid"
    When it is submitted
    Then the project stores both
```

## Delta

### ADDED

- Additive migration: `carousel_projects` (`content_mode`, `pov_thesis`, `pov_personal_proof`, `pov_format`, `slide_count`, `cta_goal`, `hook_text`, `hook_asset_id`) and `carousel_creator_assets` (`role`, `pose_tag`).
- Domain + ORM mapping; create schema validation; response fields; persona_id and strategy persisted at create.
- Wizard: Modo toggle, tese, prova, formato, nº de slides, objetivo do CTA, persona select, POV formats in the template list; i18n pt/en; component tests.

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: domain/models/carousel.py, ORM model, schemas, crud route
- Frontend: app/dashboard/create/*, constants/create.ts, schemas/carousel.ts, i18n
- Database: migration (additive, nullable)
- API: POST /api/carousels fields, response fields
- Tests: unit/integration + `carousel_content_mode.feature` + vitest
- Docs: plan §4
- Prompts/LLM: none
- Observability: none
- Deployment: manual SQL before deploy

## Dependencies

- Blocks: AE-0374, AE-0375, AE-0376
- Blocked by: AE-0372
- Related: AE-0371

## Implementation Plan

1. Gherkin
2. migration + models
3. schema + route
4. wizard + i18n + tests

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 10:00

Ticket written from the architect plan (docs/architecture/instagram-growth-pov-mode.md).

### 2026-10-15 (dev)

Implemented in 0843277, 65729df, 70d64c8 on `feat/ae-0371-growth-pov-mode`. Ready for the final relay round.

## Files Touched

Migration `b0c1d2e3f4a5`, `carousel_content_mode.py` (ORM mixin, schema), create route + `content_mode_fields.py`, workflow-start persona fallback, wizard mode/POV/persona sections, i18n, `carousel_content_mode.feature` + API/migration tests.

## Test Evidence

Static gates 16/16 PASS on `33a0884`; content-mode API + migration 344 passed; frontend PASS on `65729df`. Regression found by the consolidation suite (500 on workflow start) fixed in `70d64c8`; consolidation 71 passed.

Gate details and GATES_JSON: `.agent/reports/AE-0373.dev-summary.md` and the epic summary `.agent/reports/AE-0371.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-10-15: design per ADR-0021 and the architect plan; see the epic AE-0371 Decision Log for cross-cutting decisions.

## Blockers

None.

## Final Summary

Pending.
