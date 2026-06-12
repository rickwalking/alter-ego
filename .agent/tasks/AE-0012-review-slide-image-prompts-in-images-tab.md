# AE-0012 — Review Slide Image Prompts in Images Tab

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Frontend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-05
Updated: 2026-06-05

## Goal

Show read-only slide image prompt cards in the images tab so users can inspect the content that will drive image generation before approving the design/images gate.

## Problem

The frontend currently shows only a generic design-ready state during the design approval step. The validated AE-0010 plan adds `slide_image_prompts` to the workflow state API; the frontend needs to type that field, summarize it in artifacts, and render a review component in the images tab. The validation also warned that the behavior should get Gherkin coverage and frontend mutation testing per ADR-005.

## Scope

- Add a `SlideImagePrompt` TypeScript type.
- Add `slide_image_prompts?: SlideImagePrompt[]` to `EditorialWorkflowState`.
- Create `ImagePromptReview` component with prompt cards, slide index badge, title, and textarea content.
- Support `readOnly` so textareas are disabled during V1 review.
- Add prompt count to the workflow artifacts summary when prompts exist.
- Render `ImagePromptReview` in the images tab between artifact summary and live controls when prompts exist.
- Add i18n keys in both `en.json` and `pt.json`.
- Add a `.feature` file for the component behavior.
- Add frontend unit/integration tests and include the new component behavior in Stryker coverage.

## Non-Goals

- Submitting prompt edits.
- Persisting prompt edits to the backend.
- Changing the image generation request payload.
- Changing backend prompt exposure; covered by AE-0011.
- Reworking the full workflow panel layout.

## Acceptance Criteria

- [x] WHEN frontend types compile THE SYSTEM SHALL include `SlideImagePrompt` with `slide_index`, `title`, and `image_prompt`.
- [x] WHEN frontend types compile THE SYSTEM SHALL include `slide_image_prompts?: SlideImagePrompt[]` on `EditorialWorkflowState`.
- [x] WHEN `ImagePromptReview` receives N prompts THE COMPONENT SHALL render N prompt cards.
- [x] WHEN each prompt card renders THE COMPONENT SHALL show slide index, slide title, and prompt text.
- [x] WHEN `ImagePromptReview` receives `readOnly=true` THE COMPONENT SHALL disable all prompt textareas.
- [x] WHEN `ImagePromptReview` receives `readOnly=false` THE COMPONENT SHALL leave prompt textareas enabled for future V2 reuse.
- [x] WHEN workflow artifacts include prompts THE ARTIFACT SUMMARY SHALL show "`N image prompts ready`" using i18n.
- [x] WHEN the images tab has `slide_image_prompts` THE WORKFLOW PANEL SHALL render `ImagePromptReview` between artifact summary and live controls.
- [x] WHEN no prompts are present THE WORKFLOW PANEL SHALL preserve the existing images tab behavior.
- [x] WHEN translations are loaded THE SYSTEM SHALL provide image prompt review keys in both `en.json` and `pt.json`.
- [x] WHEN Gherkin specs are checked THE REPO SHALL include a feature file covering prompt cards, read-only textareas, and no-prompts behavior.
- [x] WHEN mutation testing runs THE NEW COMPONENT BEHAVIOR SHALL be included in Stryker scope or equivalent focused Stryker coverage.
- [x] WHEN frontend verification runs THE COMMANDS `npm run typecheck`, `npm run lint`, `npm run test -- --run`, and `npm run test:mutate` SHALL pass for the affected frontend scope.

## Gherkin Scenarios

```gherkin
Feature: Image prompt review in the images tab

  Scenario: Prompt cards render for available slide prompts
    Given workflow state includes three slide_image_prompts
    When the user opens the images tab
    Then three image prompt cards are displayed
    And each card shows the slide index, title, and prompt text

  Scenario: Prompt review is read-only during V1 approval
    Given workflow state includes slide_image_prompts
    And the prompt review is rendered with readOnly true
    When the user views each prompt textarea
    Then each textarea is disabled

  Scenario: Images tab preserves existing behavior without prompts
    Given workflow state has no slide_image_prompts
    When the user opens the images tab
    Then the image prompt review is not displayed
    And the existing artifact summary and live controls remain visible
```

## Delta

### ADDED

- `frontend/src/features/create/components/image-prompt-review.tsx`
- Frontend tests for `ImagePromptReview`.
- Integration test coverage for images tab prompt rendering.
- Gherkin feature file for image prompt review behavior.
- i18n keys for image prompt review labels and artifact count.
- Stryker coverage for the new prompt review component behavior.

### MODIFIED

- `frontend/src/features/blog/types-ai.ts`
  - Add `SlideImagePrompt` and `slide_image_prompts`.
- `frontend/src/app/dashboard/create/workspace/create-workflow-artifacts.tsx`
  - Show prompt count when prompts exist.
- `frontend/src/app/dashboard/create/workspace/create-workflow-panel.tsx`
  - Render prompt review in the images tab.
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/pt.json`
- `frontend/stryker.conf.json` if needed to include the new component/tests.

### REMOVED

None.

## Affected Areas

- Backend: no
- Frontend: yes
- Database: no
- API: consumes AE-0011 response contract
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: AE-0011
- Related: `.agent/reports/AE-0010.arch-plan.md`, `.agent/reports/AE-0010.plan-validation.md`, ADR-005 mutation testing

## Implementation Plan

1. Extend `types-ai.ts` with `SlideImagePrompt` and `slide_image_prompts`.
2. Create `ImagePromptReview` as a focused component with typed props and read-only support.
3. Add component tests for prompt count, displayed fields, disabled/enabled textarea states, and empty behavior.
4. Add an images-tab integration test proving the component renders in the correct panel position when state has prompts.
5. Add prompt count rendering to `create-workflow-artifacts.tsx`.
6. Wire `ImagePromptReview` into `create-workflow-panel.tsx` for the images view.
7. Add i18n keys to both locales.
8. Add a Gherkin `.feature` file covering the component behavior.
9. Update Stryker scope if the new component/tests are not already included.
10. Run frontend type, lint, unit, and mutation verification.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-05

- Ticket created from AE-0010 validated plan.
- Branch/worktree: `feat/ae-0003-landing-css-responsive`.
- Added `SlideImagePrompt` and `slide_image_prompts` frontend workflow state types.
- Added `ImagePromptReview` read-only prompt card component with V2-compatible `readOnly=false` behavior.
- Rendered prompt review in the images tab between artifact summary and controls when prompts exist.
- Added prompt count to artifact summary using the `"{count} image prompts ready"` i18n pattern.
- Added i18n keys in English and Portuguese, a Gherkin feature file, focused component/panel tests, and Stryker mutation scope.
- Updated workflow SSE merge helpers to preserve and map `slide_image_prompts` artifact payloads.

## Files Touched

- `frontend/src/features/blog/types-ai.ts`
- `frontend/src/constants/editorial-workflow.ts`
- `frontend/src/features/create/hooks/use-editorial-workflow-utils.ts`
- `frontend/src/features/create/hooks/use-editorial-workflow-utils.test.ts`
- `frontend/src/features/create/components/image-prompt-review.tsx`
- `frontend/src/features/create/components/image-prompt-review.test.tsx`
- `frontend/src/app/dashboard/create/workspace/create-workflow-artifacts.tsx`
- `frontend/src/app/dashboard/create/workspace/create-workflow-panel.tsx`
- `frontend/src/app/dashboard/create/workspace/create-workflow-panel.test.tsx`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/pt.json`
- `frontend/tests/features/image-prompt-review.feature`
- `frontend/stryker.conf.json`

## Test Evidence

- `npm test -- --run src/features/create/components/image-prompt-review.test.tsx src/app/dashboard/create/workspace/create-workflow-panel.test.tsx src/features/create/hooks/use-editorial-workflow-utils.test.ts` — 3 files passed, 48 tests passed.
- `npm run lint -- src/features/create/components/image-prompt-review.tsx src/features/create/components/image-prompt-review.test.tsx src/app/dashboard/create/workspace/create-workflow-panel.tsx src/app/dashboard/create/workspace/create-workflow-panel.test.tsx src/app/dashboard/create/workspace/create-workflow-artifacts.tsx src/features/blog/types-ai.ts src/features/create/hooks/use-editorial-workflow-utils.ts src/features/create/hooks/use-editorial-workflow-utils.test.ts src/constants/editorial-workflow.ts` — passed.
- `npm run typecheck` — passed.
- `npm run test:mutate` — passed; dry run 457 tests, 1405 mutants, final mutation score 81.68, no timed-out mutants. `src/features/create/components/image-prompt-review.tsx` was included in scope with 12 killed and 7 survived mutants.

## QA Report

Pending.

## Decision Log

- Treat prompt review as read-only in V1 because persistence of prompt edits is explicitly out of scope.
- Include Gherkin and Stryker coverage because both were called out as validation warnings.

## Blockers

None. AE-0011 API contract is implemented in this development pass.

## Final Summary

The images tab now shows read-only slide image prompt cards when the workflow state includes prompts, summarizes the prompt count in generated artifacts, and preserves prompt data across SSE merges.
