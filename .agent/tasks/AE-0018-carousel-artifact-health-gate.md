# AE-0018 — Carousel Artifact Health Gate

Status: Review
Tier: T2
Priority: Critical
Type: Bugfix
Area: Backend/API
Owner: Unassigned
Agent Lane: architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Prevent incomplete or placeholder carousel artifacts from reaching final approval, site publish, or Instagram publish.

## Problem

Workflow and publish paths currently trust status fields more than disk artifacts. A manually mutated project can be `approved_for_publish` while missing HD rendered slides and PDFs.

## Scope

- Add a backend artifact health service for carousel projects.
- Validate raw image files for non-CTA image slides.
- Validate standard PT/EN rendered slides for all DB slides.
- Validate HD PT/EN rendered slides for all DB slides.
- Validate PT/EN PDFs and page counts.
- Wire validation after image approval finalization.
- Wire validation into site publish and Instagram publish endpoints.

## Non-Goals

- Image generation idempotency.
- Prompt editing UI.
- Four-slide fallback removal outside publish/finalization gates.
- Changing visual design.

## Acceptance Criteria

- [ ] WHEN rendered PT slides are incomplete THE SYSTEM SHALL return a failed workflow state after image approval.
- [ ] WHEN rendered EN slides are incomplete and EN translations exist THE SYSTEM SHALL return a failed workflow state.
- [ ] WHEN HD rendered slides are missing THE SYSTEM SHALL block final completion and publish.
- [ ] WHEN PDFs are missing or page counts mismatch THE SYSTEM SHALL block final completion and publish.
- [ ] WHEN a CTA has no raw image_path but has rendered PT/EN slides THE SYSTEM SHALL NOT fail raw image validation only because of CTA.
- [ ] WHEN `POST /api/carousels/{id}/publish` runs on unhealthy artifacts THE API SHALL return 409.
- [ ] WHEN `POST /api/carousels/{id}/publish/instagram` runs on unhealthy artifacts THE API SHALL return 409.

## Gherkin Scenarios

```gherkin
Feature: Carousel artifact health gate

  Scenario: Missing HD slide blocks publish
    Given a seven-slide carousel has standard PT and EN renders
    And PT HD slide 7 is missing
    When the user publishes the carousel
    Then the API returns 409
    And the response explains the missing artifact

  Scenario: CTA without raw image passes when rendered outputs exist
    Given a seven-slide carousel has no raw image for the CTA slide
    And all rendered PT and EN slides exist
    And both PDFs have seven pages
    When artifact health is evaluated
    Then the report passes
```

## Delta

### ADDED

- `backend/src/rag_backend/application/services/carousel/artifact_health.py`
- Artifact health tests and feature file.

### MODIFIED

- `backend/src/rag_backend/application/services/carousel/editorial_finalize.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`
- `backend/src/rag_backend/api/routes/carousels/crud.py`
- `backend/src/rag_backend/api/routes/carousels/publishing.py`

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: yes
- Deployment: no

## Dependencies

- Blocks: AE-0024
- Blocked by: AE-0017
- Related: `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Add typed request/report dataclasses for artifact health.
2. Derive expected slide numbers from persisted carousel slides.
3. Reuse `filter_image_slides()` for raw image expectations.
4. Validate image files with Pillow dimensions and byte thresholds.
5. Validate PDF page counts with `pypdf`.
6. Return structured artifact errors.
7. Call the service after `re_render_slides()` before setting completed.
8. Call the service in site and Instagram publish endpoints.
9. Add focused unit and route tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

Developer implementation added the artifact health evaluator and wired it into
image-approval finalization, site publish, and Instagram publish. The workflow
now remains failed on the images phase when final rendered artifacts are
missing/corrupt instead of silently advancing.

## Files Touched

backend/src/rag_backend/application/services/carousel/artifact_health.py
backend/src/rag_backend/application/services/carousel/editorial_finalize.py
backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py
backend/src/rag_backend/api/routes/carousels/crud.py
backend/src/rag_backend/api/routes/carousels/helpers.py
backend/src/rag_backend/api/routes/carousels/publishing.py
backend/tests/unit/application/test_editorial_finalize.py

## Test Evidence

`cd backend && uv run ruff check ...` on touched backend files: passed.
`cd backend && uv run pytest tests/unit/api/test_helpers.py tests/unit/application/test_editorial_finalize.py tests/unit/api/test_editorial_workflow_state_response.py tests/unit/application/test_image_nodes.py`: 32 passed.

## QA Report

See [.agent/reports/AE-0018-AE-0023.qa.md](../reports/AE-0018-AE-0023.qa.md)

**Status**: Review
**Overall Score**: 65/100 (Grade C)

**Blocker Findings**:
- artifact_health.py has NO unit tests — 0% mutation score (378 surviving mutants)
- Editorial workflow state response test coverage exists but the artifact health gate itself is untested

**Warning Findings**:
- Private function imported across modules: `_merge_design_tokens_with_disk` from helpers
- Broad `except Exception` in `_validate_jpeg` and `_validate_pdf`
- POST /publish missing 409 in responses decorator

## Decision Log

- Artifact health is a backend source of truth, not a frontend-only warning.

## Blockers

- artifact_health.py has zero unit tests. Core gating logic is untested.

## Final Summary

Code implements the artifact health gate correctly but critically lacks unit tests for the artifact_health.py module itself. All 7 acceptance criteria are satisfied at the implementation level, but the mutation score is 0% due to missing test coverage.
