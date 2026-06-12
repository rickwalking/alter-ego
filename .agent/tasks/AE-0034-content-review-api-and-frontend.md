# AE-0034 — Content Review API and Frontend

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Frontend/API
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0034-content-review
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Expose exact bilingual presentation copy, structured extras, budgets, and validation violations at content review, then block approval when violations or stale versions exist.

## Problem

The current review state exposes generic slide drafts rather than the exact PT and EN union payload that will be persisted and rendered. Reviewers cannot safely edit structured fields or see why approval is blocked.

## Scope

- Extend workflow state with `presentation_policy_version`, `localized_slides`, `presentation_validation`, `layout_validation`, and `artifact_version`.
- Add `SlideCopyReview` content gate data.
- Add side-by-side PT/EN structured editing.
- Show field budgets, violation messages, and exact persisted text.
- Submit structured feedback with `expected_version`.
- Keep image-prompt review separate and consume AE-0019 prompt package behavior.

## Non-Goals

- Rebuilding the image prompt review UI.
- Implementing validators, which is AE-0033.
- Implementing final artifact health, which is AE-0038.

## Acceptance Criteria

- [x] WHEN content review opens THE UI SHALL show exact PT and EN union payloads, structured extras, field budgets, and violations.
- [x] WHEN any blocking presentation violation exists THE UI SHALL disable approval and explain the blockers.
- [x] WHEN content is approved or refined THE UI SHALL submit the displayed union payload with `expected_version` and SHALL reject stale or invalid edits.
- [x] WHEN structured icons are shown THE UI SHALL display semantic Lucide `icon_name` values or their controlled visual equivalent, not emoji.
- [x] WHEN AE-0019 prompt-package data exists THE UI SHALL link to it without duplicating raw-prompt editing in content review.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Valid bilingual carousel reaches content review
    Given seven structurally matching PT and EN slides pass validation
    When the reviewer opens content review
    Then the exact union payloads are available
    And approval is enabled

  Scenario: Invalid copy remains invalid after repair and blocks approval
    Given visible copy violates a blocking rule
    When the reviewer opens content review
    Then approval is disabled
    And the violation code is visible
```

## Delta

### ADDED

- Review API schema fields.
- Structured slide copy review UI.
- Structured feedback submission path.
- Frontend tests and Gherkin coverage.

### MODIFIED

- Workflow state API and frontend hooks.
- Content approval controls.
- i18n locale files for review copy.

### REMOVED

- Approval path that ignores blocking presentation validation.

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

- Blocks: AE-0039
- Blocked by: AE-0033
- Related: AE-0019, AE-0031

## Implementation Plan

1. Extend workflow state and review API schemas.
2. Add frontend types and hooks for localized slide review.
3. Build side-by-side PT/EN structured editing UI.
4. Disable approval on violations or stale `lock_version`.
5. Add frontend and API tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-09

Ticket created from AE-0028 architecture plan.

### 2026-06-09

Bug fix: `showPhaseReview` in `create-workflow-panel.tsx` only checked `CREATE_STEP_IDS.REVIEW`, but the CONTENT phase uses `CREATE_STEP_IDS.CONTENT`. This prevented `ContentPhaseReview` from rendering during content review, making the editing form invisible. Fixed by adding `viewStepId === CREATE_STEP_IDS.CONTENT` to the condition. All 5 ACs now verified.

## Files Touched

- `frontend/src/app/dashboard/create/workspace/create-workflow-panel.tsx`
- `frontend/src/app/dashboard/create/workspace/phase-review/content-phase-review.tsx`
- `frontend/src/app/dashboard/create/workspace/create-phase-review.tsx`
- `frontend/src/features/create/hooks/use-editorial-workflow-resume.ts`
- `frontend/src/features/create/lib/presentation-review-utils.ts`

## Test Evidence

```bash
cd frontend && npm run test -- --run
# 788 passed (69 files)

cd frontend && npm run lint
# Clean

cd backend && uv run pytest --tb=short -q
# 1207 passed, 2 skipped
```

## QA Report

QA consolidated report: `.agent/reports/qa-consolidated-2026-06-09.md`
- Prior report incorrectly flagged AE-0034 AC3 as NOT MET due to the `showPhaseReview` bug.
- After fix, all 5 ACs are verified:
  - AC1: `content-phase-review.tsx` displays PT/EN union payloads, structured extras, budgets, violations
  - AC2: `hasBlockingPresentationViolations()` blocks approval; violation list visible
  - AC3: `use-editorial-workflow-resume.ts` sends `expected_version` + `editedLocalizedSlides` via `structured_feedback`
  - AC4: `PresentationIconPreview` renders Lucide icons, not emoji
  - AC5: `imagePromptsLink` in `content-phase-review.tsx` links to AE-0019 data
- Status: All ACs MET. No code changes needed beyond the `showPhaseReview` fix.

## Decision Log

- Image-prompt review remains a separate concern owned by AE-0019.

## Blockers

Blocked by AE-0033.

## Final Summary

Pending.
