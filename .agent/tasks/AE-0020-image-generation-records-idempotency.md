# AE-0020 — Image Generation Records and Idempotency

Status: Review
Tier: T3
Priority: High
Type: Feature
Area: Backend/Database
Owner: Unassigned
Agent Lane: planner -> architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Persist image generation attempts and reuse successful images when prompt, model, theme, and style are unchanged.

## Problem

Retries can call OpenAI unnecessarily because the system does not persist provider metadata, deterministic generation keys, content hashes, or recoverable success/failure records.

## Scope

- Add `carousel_image_generations` persistence.
- Add domain model and repository methods.
- Store prompt payload, request metadata, response metadata, provider error metadata, output path, content hash, and timings.
- Compute deterministic `generation_key`.
- Reuse valid succeeded generation records before provider calls.
- Add recovery/backfill support from existing slide image paths.

## Non-Goals

- UI prompt editing.
- Artifact health validation.
- Changing visual design.

## Acceptance Criteria

- [ ] WHEN a provider call succeeds THE SYSTEM SHALL persist a succeeded image generation record.
- [ ] WHEN OpenAI returns no stable image ID THE SYSTEM SHALL still persist `generation_key` and `content_sha256`.
- [ ] WHEN an unchanged generation key has a valid existing file THE SYSTEM SHALL skip the provider call.
- [ ] WHEN an existing generation record points to a missing file THE SYSTEM SHALL mark it stale or failed and regenerate.
- [ ] WHEN a provider call fails THE SYSTEM SHALL persist structured `error_json`.
- [ ] WHEN recovery scans existing `image_path` files THE SYSTEM SHALL create recovered records without inventing provider IDs.

## Gherkin Scenarios

```gherkin
Feature: Image generation idempotency

  Scenario: Reuse existing successful generation
    Given a slide has a succeeded generation record
    And the output file exists and is valid
    When image generation runs with the same generation key
    Then OpenAI is not called
    And the slide image_path is reused

  Scenario: Recover existing generated image
    Given a slide has an image_path on disk
    And no generation record exists
    When the recovery command runs
    Then a recovered generation record is created
    And provider_image_id remains null
```

## Delta

### ADDED

- Database migration for `carousel_image_generations`.
- Domain model and repository protocol methods.
- Generation key/content hash utilities.
- Recovery/backfill command or script.
- Unit tests for reuse and recovery behavior.

### MODIFIED

- Image generation node/service to check generation records before provider calls.
- Repository implementation.

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: yes
- API: no
- Tests: yes
- Docs: yes
- Prompts/LLM: no
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: AE-0021, AE-0023, AE-0024
- Blocked by: AE-0019
- Related: `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Add migration and ORM model.
2. Add domain model and repository methods for create/update/find-by-generation-key.
3. Add hashing utilities for prompt, theme, and content bytes.
4. Persist pending, succeeded, failed, reused, and recovered states.
5. Check for reusable succeeded records before provider calls.
6. Backfill from existing valid `carousel_slides.image_path` files.
7. Add unit tests for all state transitions and recovery cases.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

Developer implementation added a slide-metadata idempotency foundation plus a
database-backed `carousel_image_generations` table, migration, domain model,
ORM model, repository find/upsert methods, and image-node record persistence.
Deterministic generation key, rendered prompt hash, content SHA-256, provider,
model, style, raw prompt, and rendered prompt are stored on each updated slide
and generation record. The image node reuses valid existing generation records,
recovers valid legacy image files, and records failed provider attempts. Remaining
scope: standalone recovery/backfill CLI/tooling and richer provider response
metadata such as stable provider image IDs when providers expose them.

## Files Touched

backend/src/rag_backend/application/services/carousel/image_prompt_package.py
backend/src/rag_backend/application/services/carousel/image_generation_records.py
backend/src/rag_backend/application/services/carousel/nodes/images.py
backend/src/rag_backend/domain/models/carousel_image_generation.py
backend/src/rag_backend/domain/models/__init__.py
backend/src/rag_backend/domain/protocols/repositories.py
backend/src/rag_backend/infrastructure/database/models/carousel_image_generation.py
backend/src/rag_backend/infrastructure/database/models/__init__.py
backend/src/rag_backend/infrastructure/database/carousel_repository.py
backend/alembic/versions/0007_add_carousel_image_generations.py

## Test Evidence

`cd backend && uv run ruff check ...` on touched backend files: passed.
`cd backend && uv run pytest tests/unit/application/test_image_nodes.py`: passed as part of focused backend suite.

## QA Report

See [.agent/reports/AE-0018-AE-0023.qa.md](../reports/AE-0018-AE-0023.qa.md)

**Status**: Review
**Overall Score**: 83.3% on AC (5/6 pass)

**Blocker Findings**:
- image_generation_records.py has NO unit tests — N/A mutation score
- Standalone recovery/backfill script does not exist (acknowledged remaining scope)

**Warning Findings**: None for AE-0020 scope

## Decision Log

- Use local `generation_key` and `content_sha256` as stable identifiers because the current OpenAI image response path does not expose a stable image ID.

## Blockers

- image_generation_records.py has zero unit tests. Reuse/persistence logic is untested.
- Recovery scan script not implemented (active-generation-only RECOVERED path exists).

## Final Summary

Core generation record persistence and reuse logic works correctly (5/6 AC pass). Critically missing test coverage for ImageGenerationRecords module. Recovery tooling is acknowledged remaining scope.
