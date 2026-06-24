# AE-0275 — Responsive listing & content pages

Status: Review
Tier: T2
Priority: Medium
Type: Feature
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0275-responsive-listings
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24
Parent: AE-0272
Depends-On: AE-0273

## Goal

Make the listing/content dashboard pages responsive: card grids reflow 1→2→3 columns,
fixed search widths go full-width on mobile, the analytics velocity chart stops
overflowing. Tailwind utilities only.

## Problem

- `dashboard/page.tsx:162` quick actions `gridTemplateColumns:"repeat(3,1fr)"`; `:207`
  activity `"1fr 1fr"`; `:148` inline `padding:"28px 32px"` — all frozen.
- `blog-posts-grid.tsx` featured/regular `"1fr 1fr"`; `blog-posts/page.tsx:51` search
  `w-[200px]`.
- `personas/page.tsx:49` search `w-[200px]`; `:72` grid `minmax(340px,1fr)` (forces 1 col
  <360px).
- `palettes` grid `minmax(260px,1fr)`; analytics velocity bars overflow narrow screens.

## Scope

- `dashboard/page.tsx`, `blog-posts/page.tsx` + `blog-posts-grid.tsx`,
  `personas/page.tsx`, `palettes` grid component, `analytics/page.tsx`.
- **`rubrics/rubric-panel.tsx:81,106`** (`gridTemplateColumns:"2fr 1fr 1fr 1fr"`,
  GLM tree-sweep orphan): table-like row grid must reflow/scroll on mobile
  (`overflow-x-auto` with `min-w` on the row, or stacked rows `<md`).

## Non-Goals

- Shell (AE-0273). Calendar/chat/kanban (AE-0276).

## Design decisions (from GLM 5.2 review)

- **I5 enforcement** lands in AE-0277, not here — these files become part of that gate's
  allow-list.
- **Touch targets (I6):** listing controls in scope — search inputs already full-height;
  ensure card primary actions / search clear buttons are ≥44px on coarse pointers.
- **Analytics (concrete, not vague):** wrap the velocity chart in `overflow-x-auto` with a
  `min-w` on the inner bar track so it scrolls rather than overflowing the page — the
  testable invariant is **no horizontal page overflow at 360px**.
- **`.feature` required (AE-0153):** ship the Gherkin below as a `.feature` file, not just
  inline ticket text.

## Acceptance Criteria

- [ ] Overview quick actions: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`; activity:
      `grid-cols-1 lg:grid-cols-2`; page padding `p-4 md:p-7` (or `px-4 md:px-8 py-6`).
- [ ] Blog-posts featured/regular grids: `grid-cols-1 md:grid-cols-2`; search bar
      `w-full sm:w-[200px]`.
- [ ] Personas: search `w-full sm:w-[200px]`; grid `minmax(220px,1fr)` (or
      `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) so it never forces a 1-col on small.
- [ ] Palettes grid: `minmax(200px,1fr)` (or responsive cols); cards fit at 360px.
- [ ] Analytics velocity chart: inner bar track wrapped in `overflow-x-auto` with a
      `min-w`; **no horizontal page overflow at 360px**.
- [ ] Rubrics panel row grid (`2fr 1fr 1fr 1fr`) reflows/scrolls on mobile (no frozen
      inline grid; `overflow-x-auto`+`min-w` row, or stacked `<md`).
- [ ] Layout-critical inline grid/padding/width migrated to Tailwind responsive classes.
- [ ] Neon identity unchanged; desktop visual diff ~nil; lint + typecheck + gates green.

## Gherkin Scenarios

```gherkin
Feature: Responsive dashboard listing pages

  Scenario: Quick actions reflow
    Given the dashboard overview at 375px
    Then the quick-action cards stack to one column with no overflow

  Scenario: Search bar full width on mobile
    Given the personas page at 375px
    Then the search bar spans the available width

  Scenario: Card grid columns adapt
    Given a listing page at 375 / 768 / 1280px
    Then the cards render as 1 / 2 / 3 columns respectively

  Scenario: Analytics velocity chart never overflows the page
    Given the analytics page at 375px
    Then the velocity chart scrolls within its own track and the page has no horizontal overflow

  Scenario: Palettes grid fits a phone
    Given the palettes page at 375px
    Then palette cards render at least one-up with no horizontal overflow

  Scenario: Rubrics panel row scrolls on mobile
    Given the rubrics page at 375px
    Then the 4-column rubric rows scroll horizontally or stack instead of overflowing
```

## Delta

### MODIFIED
- `dashboard/page.tsx`, `blog-posts/page.tsx`, `blog-posts-grid.tsx`,
  `personas/page.tsx`, palettes grid, `analytics/page.tsx`,
  `rubrics/rubric-panel.tsx` — inline layout → Tailwind responsive.
### ADDED
- Listing-pages `.feature` (AE-0153).

## QA Checklist

- [ ] Lint + typecheck green; tests reference scenarios.
- [ ] 360 / 768 / 1280 — grids reflow; no overflow; search bars adapt.
</content>


## Progress Log

- 2026-06-24 — Implemented per ticket scope; layout-critical inline styles migrated to
  Tailwind responsive utilities. Full `gates.sh frontend` reproduced green (17/17).

## Test Evidence

```
GATES_JSON: {"pass":17,"fail":0,"skip":0} — full frontend suite green (lint incl.
responsive-dashboard gate, boundaries, dup, component-types, i18n, typecheck, build,
test 936+, mutation, dead-files, integrity, format, schema-drift).
```

- Typecheck + targeted vitest suites pass; no new jscpd duplication; integrity 0 net-new.
