# AE-0476 — Calendar grid ARIA structure, page heading, placeholder titles, dim contrast

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-12 review follow-up
Branch: fix/ae-0476-calendar-grid-a11y
Created: 2026-10-22
Updated: 2026-10-22

## Goal

`/dashboard/calendar` passes axe: a real ARIA grid, a page h1, no placeholder chip titles, readable dim text.

## Problem

Orchestrator review of AE-0467 (#207) and the AE-0453 scan: `role="gridcell"` cells had no `row`/`grid` parents
(axe `aria-required-parent`, critical, 35 nodes), the page had no h1 (`page-has-heading-one`), placeholder titles
such as "slide" reached the chips, and the calendar's dim text (weekday headers, chip meta) was ~2.65:1.

## Scope

- `CalendarGrid`: `role="grid"` named by the viewed month; a header row of `columnheader`s; one `row` per week
  (`display: contents`, layout unchanged); the empty-month message in a row/gridcell. Day cell + chip moved to
  `calendar-day-cell.tsx` (file size).
- `CalendarHeader`: the "Calendar" title is the page h1.
- Chip titles via `resolveDisplayTitle` (placeholders → localized "Untitled").
- `CALENDAR_COLORS.tD` → `rgba(255,255,255,0.5)` (≥ 4.5:1 on header and card backgrounds).

## Non-Goals

- Toolbar behaviour/strings (AE-0454), translations (AE-0472).

## Acceptance Criteria

- [x] axe on a local build: no aria-required-parent / aria-command-name / page-has-heading-one; calendar contrast
      fixed (the remaining sidebar-label contrast is fixed by AE-0470).
- [x] Placeholder titles render "Untitled".

## Repro Steps

1. Run axe on `/dashboard/calendar`. Before: aria-required-parent ×35, no h1, contrast. After: clean (calendar).

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

Stacked on AE-0467 (#207); opened against main once #207 merges.

## Progress Log

### 2026-10-22 08:50

Failing tests first (5 red); fix; axe on a local build.

## Files Touched

- frontend/src/app/dashboard/calendar/calendar-grid.tsx, calendar-day-cell.tsx (new), calendar-header.tsx,
  page.tsx, types.ts (+ calendar-grid-a11y.test.tsx new, calendar-grid.test.tsx)
- frontend/src/modules/editorial-operations/board/calendar/helpers.ts, constants.ts (+ calendar-contrast.test.ts new)
- frontend/tests/features/calendar-grid-a11y-ae0476.feature (new)

## Test Evidence

Local frontend gates (lint, typecheck, gherkin-refs, format, integrity, dead-code, blog-v1-dead-code, duplication,
dead-files, legacy-guard, legacy-inventory, component-types, schema-drift, test 2119): PASS. Mutation: CI only.

## QA Report

Pending (CI on the PR head).

## Blockers

Waits for #207 to merge (stacked).
