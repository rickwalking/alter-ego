# AE-0003 — Landing page CSS effects and responsive layout

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0003-landing-css-responsive
Kanban Card: TBD
Created: 2026-06-02
Updated: 2026-06-03
QA Started: 2026-06-03

## Goal

Align the production marketing landing page (`/`) with the interaction and responsive behavior of `frontend/public/redesign/index.html` for **existing sections only**: hover states on buttons and cards, hero white-line glitch typography, and mobile layout (terminal-first hero stack, single-column grids).

## Problem

The live landing page uses inline styles that cannot express `:hover`, `:active`, or breakpoints. Users on mobile see a cramped two-column hero; cards and CTAs feel static compared to the hardened mockup. The hero title line lacks the glitch treatment from the reference design.

## Scope

- Tailwind utilities on `(marketing)/page.tsx` plus `@layer components` in `globals.css` (`.hero-glitch`, `.landing-cta-*`)
- Button hover/active on hero CTAs and about social links
- Card hover/active on feature cards (primary + secondary) and post cards (featured + sidebar)
- Hero glitch on `hero.titleLine1`; gradient retained on `hero.titleHighlight` only
- Responsive breakpoints at 900px and 600px (hero, stats, features, posts, about)
- `prefers-reduced-motion` guards on transforms and glitch animation
- Gherkin feature file + E2E updates for mobile hero order
- Stats numbers: solid cyan + text-shadow per DESIGN.md (not gradient)

## Non-Goals

- Neural Palettes / theme showcase section (not on live page)
- Bottom CTA section (“Ready to Connect”) from mockup
- New header nav items or footer tech-stack line
- Full migration to `NeonButton` / `NeonCard` components
- Parallax grid scroll JavaScript from mockup
- Backend or i18n copy changes

## Acceptance Criteria

- [x] Landing interactions use Tailwind + `globals.css` component classes (no CSS module)
- [x] Public post images use `toPublicCarouselImageUrl()` (no 401 preview URLs on `/`)
- [x] WHEN user hovers primary hero CTA THE control SHALL `translateY(-2px)` and intensify cyan box-shadow
- [x] WHEN user hovers ghost hero CTA THE control SHALL use cyan-dim background and `translateY(-2px)`
- [x] WHEN user hovers secondary feature card THE card SHALL show top accent line and `translateY(-4px)`
- [x] WHEN user hovers featured post card THE card SHALL `translateY(-4px)` with stronger border
- [x] WHEN user hovers sidebar post item THE background SHALL be elevated (`#111a30`)
- [x] WHEN viewport width ≤900px THE hero terminal SHALL render above hero copy (`order: -1`)
- [x] WHEN viewport width ≤900px THE features and posts grids SHALL be single column
- [x] WHEN viewport width ≤600px THE hero SHALL not use `min-height: 85vh`
- [x] WHEN landing loads THE first hero title line SHALL use glitch styling with locale-accurate `data-text`
- [x] WHEN `prefers-reduced-motion: reduce` THE hover transforms and glitch animation SHALL be disabled
- [x] Stat numbers use solid cyan with glow (no gradient text) per DESIGN.md
- [x] `cd frontend && npm run lint && npm run typecheck && npm run test -- --run` passes
- [x] `cd frontend && npm run test:e2e -- tests/e2e/home.spec.ts` passes (10 scenarios)
- [x] Root `<body>` uses `suppressHydrationWarning` for extension-injected attributes

## Gherkin Scenarios

```gherkin
Feature: Landing page CSS effects and responsive layout

  Scenario: Homepage hero stacks on mobile with terminal first
    Given the viewport width is 375
    When I open "/"
    Then the hero terminal appears above the hero heading

  Scenario: Primary CTA has hover lift on desktop
    Given the viewport width is 1280
    When I open "/"
    And I hover the "Start Chatting" link
    Then the primary CTA has a negative translateY transform

  Scenario: Reduced motion disables hover transform
    Given reduced motion is preferred
    When I open "/"
    And I hover the "Start Chatting" link
    Then the primary CTA transform is none

  Scenario: Secondary feature card lifts on hover
    Given the viewport width is 1280
    When I open "/"
    And I scroll to the capabilities section
    And I hover the first secondary feature card
    Then that card has a negative translateY transform
```

## Delta

### ADDED

- `frontend/tests/features/landing-page-effects.feature`
- `docs/plans/landing-page-css-effects-responsive.md`
- `.agent/reports/AE-0003.arch-plan.md`
- `toPublicCarouselImageUrl()` in `frontend/src/lib/carousel-media-url.ts`

### MODIFIED

- `frontend/src/app/(public)/(marketing)/page.tsx` — Tailwind hover/responsive; public image URLs
- `frontend/tests/e2e/home.spec.ts` — mobile, hover, reduced-motion, console, secondary card
- `frontend/src/app/globals.css` — glitch, CTA components, shared keyframes
- `frontend/src/app/layout.tsx` — `suppressHydrationWarning` on `<body>`
- `frontend/src/features/blog/adapters/blog-post-adapter.ts` — public image URLs
- `frontend/src/components/particle-background.tsx` — `particle-float-landing` animation name

### REMOVED

- Dead `.container-posts` media query from inline `<style>` in `page.tsx`
- Duplicate keyframes from `page.tsx` (use `globals.css`; landing particles keep `particle-float-landing`)

## Affected Areas

- Backend: None
- Frontend: `(marketing)/page.tsx`, `globals.css`, E2E, Gherkin, `carousel-media-url.ts`
- Database: None
- API: None
- Tests: `home.spec.ts`, new `.feature` file
- Docs: `docs/plans/landing-page-css-effects-responsive.md`
- Prompts/LLM: None
- Observability: None
- Deployment: None

## Dependencies

- Blocks: None
- Blocked by: None
- Related: `docs/plans/public-shell-ux-fixes.md` (public shell IA)

## Implementation Plan

Detailed plan: `docs/plans/landing-page-css-effects-responsive.md`

1. **Phase 1 — Styling:** Tailwind utilities + `globals.css` `@layer components` for pseudo-elements.
2. **Phase 2 — Buttons:** Primary/ghost hover + `:active`; social link hover in about section.
3. **Phase 3 — Cards:** Feature primary/secondary and post featured/sidebar hover rules from mockup.
4. **Phase 4 — Hero glitch:** `data-text` glitch on line 1; optional badge pulse-dot.
5. **Phase 5 — Responsive:** 900px and 600px breakpoints; `min-width: 0` on grid children.
6. **Phase 6 — Stats:** Solid cyan + text-shadow (DESIGN.md).
7. **Phase 7 — Tests:** Gherkin file, E2E mobile assertion, reduced-motion check.

## QA Checklist

- [ ] Security reviewed — N/A (presentation only)
- [ ] Code quality reviewed — no magic strings; constants for repeated rgba values in CSS module
- [ ] Acceptance criteria validated — manual hover at 1280px; mobile 375px
- [ ] Edge cases tested — long i18n strings, `prefers-reduced-motion`, touch `:active`
- [ ] Orphan/unfinished code checked — dead `.container-posts` removed

## Progress Log

### 2026-06-02

Ticket and plan created from impeccable harden audit of `redesign/index.html` vs live landing page.

### 2026-06-03 22:40

Implementation complete. Branch: `feat/ae-0003-landing-css-responsive` (local). Tailwind + globals components; responsive + hover + glitch + E2E.

### 2026-06-03 23:10

QA follow-up: ticket docs aligned to Tailwind; E2E for secondary feature card; deduplicated keyframes (`particle-float-landing`).

## Files Touched

- `frontend/src/app/(public)/(marketing)/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/layout.tsx`
- `frontend/src/lib/carousel-media-url.ts`
- `frontend/src/lib/carousel-media-url.test.ts`
- `frontend/src/features/blog/adapters/blog-post-adapter.ts`
- `frontend/src/features/blog/adapters/blog-post-adapter.test.ts`
- `frontend/src/components/particle-background.tsx`
- `frontend/tests/e2e/home.spec.ts`
- `frontend/tests/features/landing-page-effects.feature`

## Test Evidence

```bash
cd frontend && npm run lint && npm run typecheck && npm run test -- --run
# 756 passed

PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- tests/e2e/home.spec.ts
# 10 passed
```

## QA Report

**Report:** `.agent/reports/AE-0003.qa.md` (re-run 2026-06-03)

**Score:** 83/100 (Grade B)

**Status:** Review (warnings only, no blockers)

**Summary:**
- ✅ Lint, typecheck, 756 unit tests, 9/9 E2E pass
- ✅ Behavioral AC met (Tailwind + globals; CSS module superseded per user review)
- ✅ Console 401 fix via `toPublicCarouselImageUrl`; hydration `suppressHydrationWarning` on body
- 🟠 Ticket AC/dev-summary still reference deleted `landing.module.css`
- 🟠 `page.tsx` 1228 lines (pre-existing)
- 🟠 1/4 Gherkin scenarios without E2E (secondary card hover)
- 🟠 Mutation testing not run

## Decision Log

| Date | Decision | By |
|------|----------|-----|
| 2026-06-02 | Scope limited to sections on live landing (exclude theme grid, CTA) | Plan author |
| 2026-06-02 | Stats use solid cyan per DESIGN.md, not mockup gradient | DESIGN.md redline |
| 2026-06-03 | CSS module replaced with Tailwind per user review | Developer |
| 2026-06-03 | Preview image URLs mapped to public routes on marketing pages | Developer |

## Blockers

None.

## Final Summary

Landing page interactions aligned with redesign mockup using Tailwind + globals component classes. Console 401s fixed via public image URL mapping. All four Gherkin scenarios covered by E2E. Ready for re-QA / release.
