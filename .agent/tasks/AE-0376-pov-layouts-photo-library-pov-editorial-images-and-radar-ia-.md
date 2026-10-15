# AE-0376 — Pov layouts, photo library, pov_editorial images and Radar IA v7 prompts

Status: Ready
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

Render POV decks (face hook, statements, save checklist, follow CTA) with the owner's photos and cheaper images, and move new Radar IA decks to the v7 angle (roadmap R5).

## Problem

Slides use generic neon AI art on every slide, the face only appears on the CTA, and Radar IA still writes recaps.

## Scope

- Strategies `hook_face`, `statement`, `save_checklist`, `cta_follow` + CSS; role-based selection.
- Creator asset `role`/`pose_tag` on upload, list endpoint, wizard photo picker; `hook_asset_id` staged into the artifact.
- `openai__pov_editorial` preset; images node asks the policy which slides need artwork.
- `carousel/v7/{hook,outline,content}.yaml` used by projects stamped `hero_lower_third_v4`.

## Non-Goals

- Server-side background removal (rembg) — later, optional.
- Changing v3-v6 prompts.

## Acceptance Criteria

- [ ] WHEN a POV slide with role `hook` renders THE SYSTEM SHALL show the hook over the selected photo with the handle, without generated artwork.
- [ ] WHEN a POV deck renders THE SYSTEM SHALL use statement/insight/save/cta_follow layouts by role and show the `cta_goal` copy on the last slide.
- [ ] WHEN a photo is uploaded with role `hook` THE SYSTEM SHALL store the role and list it in `GET /api/carousels/creator-assets?role=hook` for its owner only.
- [ ] WHEN the image phase runs for a policy THE SYSTEM SHALL generate artwork only for slides whose policy entry has `image_required: true`.
- [ ] WHEN a Radar IA project is stamped `hero_lower_third_v4` THE SYSTEM SHALL use the v7 outline/content prompts (≤1 news slide, ≥3 impact slides, verdict close).

## Gherkin Scenarios

```gherkin
Feature: POV layouts and photos

  Scenario: Hook slide uses the owner's photo
    Given a POV project with a hook photo
    When slide 1 is rendered
    Then the slide shows the photo and the hook and no generated artwork

  Scenario: Only point slides get artwork
    Given a POV project with image preset pov_editorial and 9 slides
    When the image phase runs
    Then artwork is requested only for the 3 point slides

  Scenario: Photo library is owner scoped
    Given two users with uploaded hook photos
    When the first user lists hook photos
    Then only their photos are returned

  Scenario: Radar IA v4 uses v7 prompts
    Given a news_analysis project stamped hero_lower_third_v4
    When the outline is generated
    Then the v7 outline prompt with the angle rule is used
```

## Delta

### ADDED

- Strategies `hook_face`, `statement`, `save_checklist`, `cta_follow` + CSS; role-based selection.
- Creator asset `role`/`pose_tag` on upload, list endpoint, wizard photo picker; `hook_asset_id` staged into the artifact.
- `openai__pov_editorial` preset; images node asks the policy which slides need artwork.
- `carousel/v7/{hook,outline,content}.yaml` used by projects stamped `hero_lower_third_v4`.

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: carousel_template strategies/css/html_template, creator assets, images node, image_style_strategies, constants
- Frontend: wizard photo picker, IMAGE_PRESETS
- Database: none (columns from AE-0373)
- API: GET creator-assets list; upload role/pose
- Tests: unit + `carousel_pov_layouts.feature` + vitest
- Docs: _shared/image-generation.md, content-contracts.md
- Prompts/LLM: carousel/v7 outline/content/hook
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0377
- Blocked by: AE-0375
- Related: AE-0371

## Implementation Plan

1. Gherkin
2. strategies + css
3. role selection
4. photo library
5. images node
6. v7 prompts
7. frontend

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 10:00

Ticket written from the architect plan (docs/architecture/instagram-growth-pov-mode.md).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-10-15: design per ADR-0021 and the architect plan; see the epic AE-0371 Decision Log for cross-cutting decisions.

## Blockers

None.

## Final Summary

Pending.
