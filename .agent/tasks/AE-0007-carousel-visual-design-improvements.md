# AE-0007 — Carousel Visual Design Improvements

Status: Review
Tier: T2
Priority: High
Type: Enhancement
Area: Design
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-04
Updated: 2026-06-04

## Goal

Apply the visual design improvements from `docs/plans/carousel-style-improvements.md` (P1, P2, P5) and clean up the watermark utility duplication between `html_template.py` and the `hero_content` strategy.

## Problem

Three visual issues are unresolved from the earlier strategy refactor:
1. **Slide 7** (CTA) uses a plain dark background while slides 1-6 use full-bleed hero images — breaks visual continuity
2. **Watermark** appears on 5 slides (2-6) but research says it should be on slide 2 only
3. **Watermark utility** is duplicated in `hero_content` strategy — violates DRY
4. **Per-slide CTAs** — slide 2 lacks the swipe prompt that slide 1 has

These detract from the polished Neon Shell v2.0 look and don't follow Instagram best practices.

## Scope

- P1: Slide 7 hero-bg layout — wrap CTA content in hero-bg image + gradient structure
- P2: Watermark reduction — render on slide 2 only, remove from slides 3-6
- P5: Add directional swipe text to slide 2
- Watermark utility dedup — remove `_build_watermark()` from `hero_content` strategy, call shared `html_template._build_watermark_html()` instead
- Optional: Add top accent strip to `hero_content` strategy for News Flash template distinction

## Non-Goals

- Changing the CTA text/content (keep "Siga para mais conteúdo como esse")
- Adding mid-slide CTAs (rejected by research)
- Slide count expansion (P4)
- Mixed media (P6)

## Acceptance Criteria

- [ ] Slide 7 has hero-bg image + gradient behind the avatar/CTA layout
- [ ] Slide 7 HTML does not contain `.slide-watermark` class
- [ ] Watermark appears only on slide 2 (verified visually in HTML output)
- [ ] Slide 2 shows directional swipe text ("Deslize →" / "Swipe →")
- [ ] `hero_content` strategy no longer has its own `_build_watermark()` method
- [ ] Carousel with <7 slides gracefully skips hero-bg layout on last slide (no broken HTML)
- [ ] No visual regressions in existing slide layouts (1-6 unchanged aside from watermark)
- [ ] 866+ tests still pass after changes

## Gherkin Scenarios

```gherkin
Feature: Carousel Visual Design Improvements

  Scenario: Slide 7 has hero-bg background
    Given a carousel project with 7 slides
    When I render the CTA slide (slide 7)
    Then the slide contains ".slide-hero-bg-img" class
    And the slide contains ".slide-hero-bg-gradient" class
    And the closing avatar and CTA text are centered over the background

  Scenario: Watermark only on slide 2
    Given a rendered carousel with 7 slides
    When I inspect the HTML
    Then the watermark HTML appears in slide 2 only
    And slides 3, 4, 5, 6, 7 have no watermark

  Scenario: Slide 2 has swipe text
    Given a rendered carousel
    When I inspect slide 2 HTML
    Then the slide contains ".s1-swipe" or swipe arrow text

  Scenario: Watermark utility dedup
    Given the hero_content strategy
    When I call its render method
    Then it uses html_template._build_watermark_html() (not its own copy)

  Scenario: Graceful degradation with fewer than 7 slides
    Given a carousel project with 4 slides
    When I render all slides
    Then slide 4 (the last slide) does not use hero-bg layout
    And no HTML error or missing-class occurs
```

## Delta

### ADDED

- Slide 7 hero-bg CSS selectors for centered content overlay
- Slide 2 swipe text in `hero_content` strategy

### MODIFIED

- `strategies/cta.py` — wrap content in hero-bg structure
- `strategies/hero_content.py` — remove `_build_watermark()`, import shared utility
- `html_template.py` — export `_build_watermark_html` for reuse
- `css/slide_styles.py` — add `.slide-hero-content .closing-*` centered positioning overrides
- `css/responsive.py` — ensure responsive breakpoints handle new slide 7 layout

### REMOVED

- `_build_watermark()` method from `hero_content` strategy

## Affected Areas

- Backend: yes (HTML + CSS in carousel_template)
- Frontend: no
- Database: no
- API: no
- Tests: no
- Docs: no
- Prompts/LLM: no
- Observability: no
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: none (independent of AE-0005/AE-0004/AE-0006)
- Related: AE-0005 (touches same dispatch code — coordinate merge order)

## Implementation Plan

1. Export `_build_watermark_html` from `html_template.py` (add to `__all__`)
2. Update `hero_content` strategy to import and use the shared utility; remove its own `_build_watermark()`
3. Add CSS for slide 7 hero-bg layout: `.slide-hero-content .closing-avatar` centered, `.slide-hero-content .closing-name`, `.slide-hero-content .closing-cta` with proper z-index
4. Update `cta_centered` strategy: wrap inner HTML in hero-bg structure (same as hero_content but with centered content)
5. Add swipe text to `hero_content` strategy for slide 2 (check `slide["number"] == 2`)
6. Pass `slide_number` context to remove watermark from slides 3+ (or add `include_watermark` param)
7. Update responsive CSS for new slide 7 layout at 640px/400px breakpoints
8. Verify all 866+ tests pass

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-04

Ticket created. Design spec in §11 of `docs/plans/carousel-slide-layout-strategies.md`.

### 2026-06-04 — Implementation

All 5 ACs implemented:

- `html_template.py`: Exported `_build_watermark_html` in `__all__` for reuse
- `cta.py`: Wrap CTA slide in hero-bg image + gradient when `total_slides >= 7`; add `.is-centered` CSS class
- `hero_content.py`: Removed `_build_watermark()` method, imported shared `_build_watermark_html`; watermark only on slide 2; swipe text on slide 2
- `slide_styles.py`: Added `.slide-hero-content.is-centered` (centered layout for CTA), `.slide-hero-content .s1-swipe` (swipe text), `.is-centered .creator-watermark` left override
- All constants extracted to module level: `_MIN_SLIDES_FOR_HERO_BG`, `_WATERMARK_SLIDE_NUMBER`, `_SWIPE_TEXT`
- 866 tests pass, 0 regressions, ruff clean

## Files Touched

Pending.

## Test Evidence

```bash
cd backend
uv run pytest tests/unit/application/test_carousel_template_builder.py -v
uv run ruff check src/
```

## QA Report

See `.agent/reports/AE-0007.qa.md` — **Overall: 87/100 (Grade B)**

| Dimension | Status |
|-----------|--------|
| Security | ✅ PASS (100/100) |
| Code Quality | 🟠 WARN (70/100 — 1 pre-existing blocker, 1 warning) |
| Mutation Testing | ⚪ N/A (no tests for strategies; AE-0006 adds them) |
| Acceptance Criteria | ✅ PASS (100/100 — 8/8 criteria met) |
| Orphan/Unfinished Code | ✅ PASS (95/100) |

**Findings:** No blockers introduced by AE-0007. 1 pre-existing file size issue, 1 magic string in unrelated code. 2 suggested fixes for i18n swipe text.

## Decision Log

- Watermark on slide 2 only follows improvement plan P2
- Slide 7 hero-bg follows improvement plan P1 with centered avatar/CTA overlay
- No new strategy needed — existing `cta_centered` and `hero_content` strategies are modified in place
- Slide 7 does NOT get the page-level watermark (avatar already identifies creator)

## Blockers

None.

## Final Summary

Pending.
