# AE-0372 — Radar IA quick fixes: deslize, caption v7, cta copy, slide counter, image defaults

Status: In Development
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

Ship the Radar IA quick fixes of plan 16.4 #3-#7 (roadmap R1).

## Problem

PT slides say "Swipe →"; the caption prompt asks for 12-18 PT/EN hashtags and a double CTA; the CTA slide copy is a fixed generic line; the counter renders `0{n}` so slide 10 would read "010 / 10"; the UI defaults to Comic Neon while the backend and autopilot default to Neo Anime; the outline skill's model example is a news headline.

## Scope

- `SWIPE_TEXT_PT` / `CAROUSEL_SWIPE_TEXT_PT` = "Deslize →" and PT slides use it.
- New `carousel/v7/caption_prompt.yaml` (3-5 hashtags, mostly PT, one CTA, hook on line 1, search keywords); `build_caption_prompt` renders v7 through a named constant.
- CTA copy variants (follow/send/comment) as PT/EN constants; Radar IA CTA slide uses the follow variant in `strategies/cta.py` and `slides.py`.
- One counter formatter `{n:02d} / {total:02d}` used by every counter site.
- Image default `flat_editorial` in backend, autopilot and the wizard.
- `phases/outline/SKILL.md` examples become POV-style hooks; `_shared/export-and-caption.md` documents the new caption rules.

## Non-Goals

- Editing caption v1/v2 or any existing prompt file.
- Changing captions already generated.

## Acceptance Criteria

- [ ] WHEN a PT slide renders a swipe hint THE SYSTEM SHALL show "Deslize →"; EN slides SHALL keep "Swipe →".
- [ ] WHEN a caption prompt is built THE SYSTEM SHALL render `carousel/v7/caption_prompt` which asks for 3-5 hashtags, a single CTA and the hook on line 1.
- [ ] WHEN a Radar IA CTA slide renders THE SYSTEM SHALL show the follow variant in its locale instead of "Siga para mais conteúdo como esse".
- [ ] WHEN slide 10 of 10 renders THE SYSTEM SHALL show "10 / 10" and slide 3 of 7 "03 / 07".
- [ ] WHEN no image style is given THE SYSTEM SHALL use `flat_editorial` in the API, the autopilot and the wizard.

## Gherkin Scenarios

```gherkin
Feature: Radar IA quick fixes

  Scenario: Portuguese swipe hint
    Given a PT carousel intro slide
    When it is rendered
    Then the footer shows "Deslize →"

  Scenario: Double-digit slide counter
    Given a 10-slide carousel
    When slide 10 is rendered
    Then the counter reads "10 / 10"

  Scenario: Caption v7 keeps hashtags short
    Given a carousel with slide headings
    When the caption prompt is built
    Then the prompt asks for 3 to 5 hashtags and a single call to action

  Scenario: CTA slide uses the follow variant
    Given a PT Radar IA carousel
    When the CTA slide is rendered
    Then it shows "Siga @pedromarins.ai: toda terça e quinta eu traduzo IA em decisões reais."

  Scenario: Missing image style falls back to flat editorial
    Given a create request without an image style
    When the project is created
    Then its image style is "flat_editorial"
```

## Delta

### ADDED

- `SWIPE_TEXT_PT` / `CAROUSEL_SWIPE_TEXT_PT` = "Deslize →" and PT slides use it.
- New `carousel/v7/caption_prompt.yaml` (3-5 hashtags, mostly PT, one CTA, hook on line 1, search keywords); `build_caption_prompt` renders v7 through a named constant.
- CTA copy variants (follow/send/comment) as PT/EN constants; Radar IA CTA slide uses the follow variant in `strategies/cta.py` and `slides.py`.
- One counter formatter `{n:02d} / {total:02d}` used by every counter site.
- Image default `flat_editorial` in backend, autopilot and the wizard.
- `phases/outline/SKILL.md` examples become POV-style hooks; `_shared/export-and-caption.md` documents the new caption rules.

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: domain/constants/carousel.py, blog_language.py, carousel_template/*
- Frontend: constants/create.ts default preset
- Database: none (server_default of image_style unchanged; API default changes)
- API: default image_style
- Tests: unit + feature `radar_ia_quick_fixes.feature`
- Docs: carousel-pipeline outline SKILL + export-and-caption
- Prompts/LLM: carousel/v7/caption_prompt.yaml
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0373
- Blocked by: none
- Related: AE-0371

## Implementation Plan

1. Gherkin
2. constants + formatter
3. caption v7 + builder
4. CTA copy
5. defaults
6. docs

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
