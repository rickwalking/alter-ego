# AE-0024 — Clean Carousel Regeneration QA

Status: Review
Tier: T2
Priority: High
Type: QA
Area: QA/Integration
Owner: Unassigned
Agent Lane: qa -> release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-08
Updated: 2026-06-08

## Goal

Validate that a clean carousel workflow run produces complete image, render, PDF, preview, and publish artifacts without manual DB or file edits.

## Problem

Previous validation was contaminated by manual placeholder generation, manual DB status changes, wrong project ID targeting, and changed admin credentials.

## Scope

- Reset or create a clean target carousel.
- Run the normal workflow start/resume sequence without manual DB status edits.
- Verify image generation reuse and provider error behavior where applicable.
- Verify rendered PT/EN standard and HD slides.
- Verify PDFs and page counts.
- Verify workspace preview, publish preview, and API design responses expose complete rendered slide sets.
- Run `scripts/carousel_visual_qa.py`.
- Attach QA evidence.

## Non-Goals

- Implementing backend fixes.
- Changing visual design beyond already implemented work.
- Publishing to real external social media unless explicitly approved.

## Acceptance Criteria

- [ ] WHEN a clean carousel completes THE DB SHALL have the expected slide count.
- [ ] WHEN raw image generation completes THE non-CTA image slides SHALL have valid image_path values.
- [ ] WHEN export completes THE output dir SHALL contain PT and EN standard slides for all DB slides.
- [ ] WHEN export completes THE output dir SHALL contain PT and EN HD slides for all DB slides.
- [ ] WHEN export completes THE PT and EN PDFs SHALL exist and have expected page counts.
- [ ] WHEN preview design endpoints are requested THE RESPONSES SHALL include complete rendered_slides_pt and rendered_slides_en lists.
- [ ] WHEN visual QA runs THE COMMAND `scripts/carousel_visual_qa.py` SHALL pass.
- [ ] WHEN publish is attempted on an incomplete artifact set THE API SHALL reject it.

## Gherkin Scenarios

```gherkin
Feature: Clean carousel regeneration QA

  Scenario: Clean run produces complete rendered outputs
    Given the carousel workflow starts from a clean project
    When all review gates are approved
    Then PT and EN rendered slides exist for every DB slide
    And HD rendered slides exist for every DB slide
    And visual QA passes

  Scenario: Incomplete artifact set is rejected
    Given a carousel is missing one HD rendered slide
    When the user attempts to publish
    Then the API returns a conflict
```

## Delta

### ADDED

- QA evidence for clean regeneration.
- Contact sheets or screenshots as applicable.

### MODIFIED

- QA report and task progress logs.

### REMOVED

None.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: yes
- API: yes
- Tests: yes
- Docs: yes
- Prompts/LLM: yes
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: release
- Blocked by: AE-0018, AE-0020, AE-0021, AE-0022, AE-0023
- Related: AE-0017, `.agent/reports/carousel-generation-recovery-plan.md`

## Implementation Plan

1. Confirm credentials and environment are clean.
2. Choose a target project or create a new one.
3. Run the normal workflow through all gates.
4. Verify DB rows and output files.
5. Verify preview/publish API responses.
6. Run visual QA and inspect contact sheets.
7. Write `.agent/reports/AE-0024.qa.md` with evidence.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-08

Ticket created from AE-0017 epic.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Clean QA must not rely on GLM's placeholder carousel as a passing baseline.

## Blockers

Waiting for implementation tickets.

## Final Summary

Pending.
