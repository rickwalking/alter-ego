# AE-0283 — calendar month navigation: replace static may-2026 mockup with real date state

Status: Intake
Tier: T2
Priority: P1
Type: Bugfix
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

The dashboard content calendar reflects a REAL, navigable month: the title and
grid follow the actually-viewed month (defaulting to the current month), the
prev/next/Today buttons change the month, and scheduled items appear on their
true calendar date. Replace the hardcoded "May 2026" static demo with derived
date state.

## Problem

(Reported by the user; reproduced via Playwright MCP at 1440 on 2026-06-25 —
screenshot `calendar-bug-may2026-stuck.png`.)

The calendar is a **static mockup with no date state at all**:
- `frontend/src/app/dashboard/calendar/calendar-toolbar.tsx:36` hardcodes
  `<h2>May 2026</h2>`; the Previous/Next/Today buttons (lines 15–52) have **no
  `onClick`** — clicking "Next month" leaves the title at "May 2026" (verified).
- `frontend/src/modules/editorial-operations/board/calendar/constants.ts`
  hardcodes the whole grid: `CALENDAR_TODAY = 28`,
  `CALENDAR_LEADING_DAYS = [27,28,29,30]`, `CALENDAR_LAST_DAY = 31`.
- `helpers.ts:buildMonthGridShell()` always emits that one fixed grid regardless
  of month/year, and `buildCalendarDaysFromApi()` places events by
  `parseISO(item.event_date).getDate()` — **day-of-month only**, so an event in
  any month lands on the static grid and months bleed together.

The backend is NOT at fault: `GET /api/content-calendar`
(`backend/.../api/routes/content_calendar.py:76`) already accepts `start`/`end`
datetime query params and returns items with a full ISO `event_date`. The
frontend hook `useCalendarDays` calls `useContentCalendar()` with **no args**, so
it never scopes to a month. This is a **frontend-only** fix.

This is exactly the class memory `cross-layer-validation-gap` and the AE-0272
learnings warn about — UI shipped as a visual shell that compiles green but has no
real behavior. No automated gate caught it.

## Scope

Frontend only. In `frontend/src/app/dashboard/calendar/` and the calendar module:

1. **Date state.** Introduce a `viewedMonth` state (anchor `Date` = first of the
   month), initialized to the real current month (`startOfMonth(new Date())`).
   Lift it to the calendar page (or a small `useCalendarMonth` hook) so the
   toolbar and the days-hook share it.
2. **Derived month grid.** Replace `buildMonthGridShell()`'s hardcoded constants
   with a pure function `buildMonthGrid(anchor: Date)` using `date-fns`
   (already a dep): leading days from the previous month to the week start,
   the anchor month's days, trailing days to complete the final week (6-week /
   42-cell stable grid preferred to avoid layout jump). Each cell carries its
   full `date` (ISO) plus `cur` (in-month) and `today` (= real today) flags.
3. **Wire the controls.** Prev → `subMonths(anchor,1)`; Next → `addMonths(anchor,1)`;
   Today → `startOfMonth(new Date())`. Render the title from the anchor
   (`format(anchor, "MMMM yyyy")`).
4. **Scope the fetch + match events by full date.** `useCalendarDays` passes the
   visible grid's `start`/`end` (first/last visible cell) to `useContentCalendar`,
   and matches each item to a cell by full `yyyy-MM-dd` (not `getDate()`), so
   events show only in their real month.
5. **Preserve the Neon visual identity** exactly (colors, spacing, weekday
   headers, legend, empty-state) — only the data wiring changes.

## Non-Goals

- **Week / Day view modes.** The Month/Week/Day buttons are also inert, but
  switching views is a separate feature. Keep "Month" active; leave Week/Day for
  a follow-up ticket (note it). Do not implement them here.
- **i18n of the calendar.** The whole calendar is currently hardcoded English
  ("Calendar", "Sync", weekday headers, view modes). Month name via
  `format(...,"MMMM yyyy")` matches that existing (non-i18n) state. A full i18n
  pass is out of scope — file a follow-up if desired (do not expand scope here).
- Any backend / API change.
- Drag-to-schedule, event editing, or the "Schedule Post" / "Sync" actions.

## Acceptance Criteria

- [ ] On load, the title and grid show the **current** month (today = highlighted
      real day), not a hardcoded "May 2026".
- [ ] Clicking **Next month** / **Previous month** changes the title and grid by
      one month; **Today** returns to the current month. Verified via Playwright
      MCP at 390 + 1440 (title text changes; grid leading/trailing days + today
      highlight recompute correctly across a month with a different weekday start,
      e.g. Feb and a 31-day month).
- [ ] Scheduled items render on their **true** calendar date and only in the
      month that contains them (no day-of-month bleed across months).
- [ ] The fetch is scoped to the visible window (`start`/`end` passed to
      `/api/content-calendar`).
- [ ] Pure grid/event-matching logic is **unit-tested** (`.feature`-backed):
      leading/trailing day computation, today flag, 28/30/31-day + leap-Feb
      months, and event-to-cell matching by full date.
- [ ] Neon visual identity unchanged; `npm run lint` + `npm run typecheck` +
      `npm run test` green; full `bash scripts/ci/gates.sh frontend` green.
- [ ] No new horizontal overflow at 390 (per AE-0272 landmines: the month grid is
      a scroll region — keep `min-w-0` ancestors intact).

## Gherkin Scenarios

```gherkin
Feature: Calendar month navigation

  Scenario: calendar opens on the current month
    Given today is in June 2026
    When I open the content calendar
    Then the title reads "June 2026"
    And today's date cell is highlighted

  Scenario: navigating to the next month
    Given the calendar shows "June 2026"
    When I click "Next month"
    Then the title reads "July 2026"
    And the grid shows July's days with correct weekday alignment

  Scenario: returning to today
    Given the calendar shows a month other than the current one
    When I click "Today"
    Then the title returns to the current month
    And today's cell is highlighted again

  Scenario: events appear on their real date
    Given a carousel is scheduled for 2026-07-10
    When I navigate to July 2026
    Then the event appears on the 10th
    And it does not appear in June or August
```

## Delta

### ADDED

- `buildMonthGrid(anchor)` pure helper + a `useCalendarMonth` (or page-level)
  month-state hook
- unit tests for grid + event-matching; `.feature` file
- a `date`/ISO field on the calendar day cell

### MODIFIED

- `frontend/src/app/dashboard/calendar/calendar-toolbar.tsx` (real title +
  wired prev/next/Today via props)
- `frontend/src/app/dashboard/calendar/page.tsx` (own/lift month state)
- `frontend/src/app/dashboard/calendar/use-calendar-days.ts` (scope fetch to
  visible window; match events by full date)
- `frontend/src/modules/editorial-operations/board/calendar/helpers.ts`
  (`buildMonthGrid(anchor)` replacing the hardcoded shell)
- `frontend/src/modules/editorial-operations/board/calendar/types.ts` (cell gains
  a `date`)
- `frontend/src/app/dashboard/calendar/calendar-grid.tsx` (consume `date` if
  needed)

### REMOVED

- Hardcoded `CALENDAR_TODAY` / `CALENDAR_LEADING_DAYS` / `CALENDAR_LAST_DAY`
  constants and the static `"May 2026"` literal (replaced by derived state).

## Affected Areas

- Backend: none
- Frontend: calendar page, toolbar, grid, days-hook, helpers, constants
- Database: none
- API: none (uses existing `start`/`end` params of `/api/content-calendar`)
- Tests: unit tests for grid + event matching; `.feature` file; Playwright check
- Docs: none (calendar has no dedicated doc)
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0272 (responsive dashboard — keep `min-w-0` overflow rules),
  AE-0278 (calendar `<md` agenda view follow-up), memory
  `cross-layer-validation-gap`. Follow-up: Week/Day view modes + calendar i18n.

## Implementation Plan

1. Add `buildMonthGrid(anchor: Date)` in `helpers.ts` (date-fns:
   `startOfMonth`/`endOfMonth`/`startOfWeek`/`endOfWeek`/`eachDayOfInterval`/
   `isSameMonth`/`isToday`); unit-test it against 28/30/31-day + leap-Feb months.
2. Add month state (page-level or `useCalendarMonth`) defaulting to the current
   month; thread an `onChange`/anchor down to the toolbar.
3. Wire toolbar prev/next/Today + render `format(anchor,"MMMM yyyy")`.
4. Update `useCalendarDays` to derive the visible window and pass `start`/`end`
   to `useContentCalendar`; match items to cells by `yyyy-MM-dd`.
5. Write the `.feature` + unit tests; run `gates.sh frontend`; verify via
   Playwright MCP at 390 + 1440 (navigate Jun→Jul→Feb, Today, event placement).

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-25 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
