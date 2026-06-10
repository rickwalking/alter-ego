# Image Phase Resilience and Prompt Review Epic

Status: Intake
Tier: T3
Source Plan: `.agent/reports/AE-0010.arch-plan.md`
Validation: `.agent/reports/AE-0010.plan-validation.md`
Validation Status: PASS
Created: 2026-06-05

## Goal

Make the design/images workflow resilient to artifact failures and give users meaningful image prompt content to review before approving image generation.

## Problem

The validated AE-0010 plan identifies two coupled issues:

1. `design_phase_async` and `images_phase_async` do not mirror the existing `content_phase_async` failed-artifact guard, so artifact failures can escape into the background runner and become opaque workflow failures.
2. The design approval step shows no meaningful image-generation content even though slide image prompts are already generated and persisted in `CarouselSlide.image_prompt`.

## V1 Scope

- Add failed-status guards to `design_phase_async` and `images_phase_async`.
- Catch `apply_design_tokens()` failures inside design artifact creation and return a workflow failure state.
- Expose persisted slide image prompts through the workflow state API for design/images phases.
- Render read-only image prompt review cards in the frontend images tab.
- Add backend, frontend, Gherkin, and mutation-test coverage called out by the validation report.

## Non-Goals

- Editing or submitting image prompt changes in V1.
- Persisting prompt edits back to `CarouselSlide.image_prompt`.
- Changing the image generation phase to consume edited prompts.
- Adding phase-level retry or auto-retry behavior.
- Adding database migrations; prompts already live on existing slide records.

## Ticket Breakdown

| Ticket | Title | Tier | Area | Summary | Dependencies |
|--------|-------|------|------|---------|--------------|
| AE-0010 | Guard Design and Images Phase Failures | T2 | Backend | Add failed-status guards and design token failure handling. | None |
| AE-0011 | Expose Slide Image Prompts in Workflow State | T2 | Backend/API | Add response schema, route-side slide fetching, and builder mapping for prompts. | AE-0010 |
| AE-0012 | Review Slide Image Prompts in Images Tab | T2 | Frontend | Add frontend type, review component, artifact count, tab wiring, i18n, Gherkin, and Stryker coverage. | AE-0011 |

## Acceptance Criteria Mapping

- AE-0010 covers validation AC-1 through AC-5.
- AE-0011 covers validation AC-6 through AC-11.
- AE-0012 covers validation AC-12 through AC-17, plus the validation warnings for a component `.feature` file and frontend mutation coverage.

## Suggested Execution Order

1. AE-0010: Make workflow failure handling deterministic before adding more response behavior.
2. AE-0011: Expose prompts through the API with graceful degradation.
3. AE-0012: Render prompts in the images tab once the API contract exists.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Prompt data is stale after slide regeneration | User may review older prompt wording | Fetch prompt records from current slide rows at response time. |
| Route-side slide query fails | Workflow state endpoint could become brittle | Degrade to `slide_image_prompts = None` and keep the state response working. |
| Users expect editable prompts to persist | V1 UX could imply edits are saved | Render review as read-only in V1 and keep edit persistence as a V2 follow-up. |
| Frontend mutation coverage is missed | ADR-005 quality gate is under-enforced | Add the new component path to Stryker scope or otherwise include focused mutation coverage. |

## Handoff

Use `.agent/reports/AE-0010.arch-plan.md` and `.agent/reports/AE-0010.plan-validation.md` as the source of truth for implementation. The plan has already passed architecture validation; each child ticket should still be implemented through the normal architect -> developer -> qa -> release lane.
