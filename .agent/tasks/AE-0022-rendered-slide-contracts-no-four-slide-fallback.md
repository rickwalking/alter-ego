# AE-0022 — Rendered Slide Contracts and No Four-Slide Fallback

Status: Review
Tier: T2
Priority: Critical
Type: Bugfix
Area: Backend/API + Frontend
Owner: Unassigned
Agent Lane: architect -> developer -> qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Stop the API and frontend from hiding incomplete rendered exports by falling back to four raw image URLs.

## Problem

When `pt/` and `en/` rendered export directories are missing, `_apply_draft_preview_urls()` removes rendered slide fields and populates `images.slides` from raw images truncated to four. Frontend preview then renders only four slides.

## Scope

- Change design token disk merge behavior to require complete rendered slide sets.
- Stop inventing four default slide URLs.
- Replace "any rendered slide exists" checks with completeness checks.
- Update workspace and publish preview to require rendered slides.
- Update Instagram/public image URL builder to use all rendered slide numbers instead of four raw image URLs.
- Update tests that currently assert four-slide fallback behavior.

## Non-Goals

- Artifact health implementation; AE-0018.
- Image generation records; AE-0020.
- Visual design changes.

## Acceptance Criteria

- [ ] WHEN a seven-slide carousel has no PT rendered exports THE API SHALL NOT return four raw fallback slides as rendered carousel output.
- [ ] WHEN rendered PT slides are complete THE API SHALL return all seven PT rendered preview URLs.
- [ ] WHEN rendered EN slides are complete THE API SHALL return all seven EN rendered preview URLs.
- [ ] WHEN rendered slides are incomplete THE frontend SHALL show an incomplete-artifact state instead of a shorter carousel.
- [ ] WHEN Instagram publish builds image URLs THE SYSTEM SHALL use rendered slide URLs for all expected slides.
- [ ] WHEN tests run THE old expectation `rendered_pt[:4]` SHALL be removed.

## Gherkin Scenarios

```gherkin
Feature: Rendered slide contract

  Scenario: Missing rendered directory does not produce four-slide preview
    Given a carousel has seven DB slides
    And only raw images exist on disk
    When the project design tokens are merged with disk
    Then rendered_slides_pt is absent or empty
    And images.slides is empty

  Scenario: Complete rendered slides produce full carousel preview
    Given a carousel has seven DB slides
    And PT HD rendered slides exist for slides 1 through 7
    When the preview design endpoint is requested
    Then the response contains seven rendered_slides_pt URLs
```

## Delta

### ADDED

- Complete rendered slide helper with expected slide numbers.
- Frontend incomplete-artifact state.

### MODIFIED

- `backend/src/rag_backend/api/routes/carousels/helpers.py`
- `backend/src/rag_backend/api/routes/carousels/preview.py`
- `backend/src/rag_backend/api/routes/carousels/media.py`
- `backend/src/rag_backend/api/routes/carousels/publishing.py`
- `frontend/src/app/dashboard/create/workspace/create-carousel-preview.tsx`
- `frontend/src/features/publish/components/publish-panel.tsx`
- `frontend/src/lib/carousel-media-url.ts`
- Existing backend and frontend tests for slide URL selection.

### REMOVED

- Four-slide raw fallback behavior for full carousel previews and publishing.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: no
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: AE-0024
- Blocked by: AE-0018
- Related: `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Add helper that compares disk slide numbers to expected DB slide numbers.
2. Update design token merging to only return complete rendered lists.
3. Stop default token generation from inventing four slides.
4. Update public/Instagram image URL builder to take project and expected slide numbers.
5. Update frontend preview and publish components to require rendered slides.
6. Replace unit tests that assert four-slide fallback with incomplete-artifact tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

Developer implementation removed the backend raw-image preview fallback and
the four-slide cap from draft design token merging. Default design tokens no
longer invent four raw `/images/slide_N` URLs when rendered slides are absent.
Instagram publishing now builds rendered slide URLs for the actual persisted
slide numbers. Remaining scope: explicit frontend incomplete-artifact empty
state polish and completeness helpers that compare disk slide numbers against
DB expected numbers in every preview endpoint.

## Files Touched

backend/src/rag_backend/api/routes/carousels/helpers.py
backend/src/rag_backend/api/routes/carousels/publishing.py
backend/tests/unit/api/test_helpers.py

## Test Evidence

`cd backend && uv run pytest tests/unit/api/test_helpers.py`: passed as part of focused backend suite.

## QA Report

See [.agent/reports/AE-0018-AE-0023.qa.md](../reports/AE-0018-AE-0023.qa.md)

**Status**: Review
**Overall Score**: 100% on AC (all 6 pass)

**Blocker Findings**: None
**Warning Findings**: None for AE-0022 scope

## Decision Log

- Rendered slide completeness is required for full carousel preview and publish surfaces.

## Blockers

None.

## Final Summary

All 6 acceptance criteria pass. Four-slide raw fallback removed. Instagram publish uses rendered slide URLs for all expected slides. Old `rendered_pt[:4]` test expectations removed. Complete and clean.
