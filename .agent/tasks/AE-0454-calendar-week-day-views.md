# AE-0454 — Calendar: Week and Day views

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-05 (part 1 of 3)
Branch: feat/ae-0454-calendar-views
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The Week and Day buttons on `/dashboard/calendar` work: they show the focused week or day from the same
content-calendar data as the month, in the viewer's timezone, on desktop and at 375 px, in pt and en.

## Problem

Found by the AE-0453 site scan (SITE-05). `calendar-toolbar.tsx` rendered Month / Week / Day buttons without an
`onClick`, and Month was hard-coded as active. Pedro decided to build Week, Day, Sync and Schedule Post; this
ticket's PR is the first of three (Week + Day). Schedule Post and Sync follow in their own PRs.

## Scope

- Toolbar state in the URL: `?view=week|day` (month is the default and stays out of the URL) and
  `?date=yyyy-MM-dd` (the focused day; absent means today). Reload and shared links keep the range;
  changing the view or opening a day pushes a history entry so Back restores the previous view
  (prev / next / Today replace the entry).
- Previous / Next step by month, week or day; labels follow the view ("Next week"). Today drops the date.
- Week view: seven day columns (stacked rows below `md`); a day header opens that day in the day view.
- Day view: the day's items in order, with local time (date-only items say "All day"), "Untitled" for an
  item without a title, the month grid's type/status labels, and an empty state.
- View buttons are a labelled group with `aria-pressed`; the title is `aria-live`.
- The fetch window follows the view (week / day only), padded one day on each side as before.
- Items with a time of day are placed on the viewer's LOCAL date in every view (the month grid used the UTC
  date prefix, which put 22:00 BRT on the next day); date-only items keep their date.
- pt and en strings for the toolbar and the new views.

## Non-Goals

- Schedule Post dialog and Sync (separate PRs under this ticket).
- Translating the rest of the calendar header / month chips (SITE-13), raw HTML in titles (SITE-12),
  today-in-UTC (SITE-04, AE-0462).

## Acceptance Criteria

- [x] Month is the default; Week and Day render their views and are pressed when active.
- [x] View and date are read from and written to the URL.
- [x] Prev / Next / Today move by the view's unit; a week day header opens the day view.
- [x] Items show on their local date with local times; date-only items are "All day".
- [x] Week columns stack at 375 px; everything is reachable by keyboard.
- [x] pt and en labels.

## Gherkin Scenarios

`frontend/tests/features/calendar-week-day-views.feature`; `calendar-month-navigation.feature` (the
"UTC time component" scenario is replaced by local-date and date-only scenarios).

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

AE-0462 (PR #195, calendar today in the local timezone) touches the same hooks; this branch is rebased on it.

## Progress Log

### 2026-10-22

Week + Day views, URL state, local-date placement, tests. Review fixes: rebase on #216 + #220, untitled
fallback, #216's type/status keys reused (agenda duplicates removed), Back restores the view, TZ restored
correctly in tests (calendar tests pass with TZ=America/Sao_Paulo and TZ=UTC).

### 2026-10-22 (PR 2 — Schedule Post)

Pedro: Schedule Post schedules approved blog posts only, through the existing
`POST /api/blog-posts/{id}/schedule` (no backend change). The header button opens a dialog: one page of
approved posts, a `datetime-local` field in the viewer's timezone (named under it, min = now + 1 min),
client validation (post, time, at least a minute ahead), a warning for other posts publishing within an
hour, `If-Match` with the post's lock version, and 400/409/422/other errors explained. Success closes the
dialog, re-fetches the calendar and shows a notice. Scenarios: `calendar-schedule-post.feature`.
Review fixes: conflicts come from the content calendar for the chosen time ±1 h, inclusive (the blog list has
no schedule times), so carousels count too; drafts and posts under review are listed disabled with
"approve it first"; NeonModal traps focus (moves in on open, Tab stays inside, focus returns on close).

### 2026-10-22 (PR 3 — Sync)

Pedro: Sync = refresh now. The header's Sync button re-fetches the visible range (`useContentCalendar`
refetch), is busy/disabled while running, then shows "Synced at HH:MM" (hidden while a load error is
shown). pt/en labels. Scenarios: `calendar-sync.feature`. Review fix: `useContentCalendar.refetch` now
resolves true only when its response was stored, and Sync records the time only then (try/finally for the
busy state), so a failed or aborted sync never shows a new "Synced at".

## Files Touched

- frontend/src/app/dashboard/calendar/* (toolbar, page, view body, week/day views, agenda event, hooks, tests)
- frontend/src/modules/editorial-operations/board/calendar/{constants,helpers,types,view-helpers}.ts (+ tests)
- frontend/src/i18n/locales/{en,pt}.json
- frontend/tests/features/calendar-week-day-views.feature, calendar-month-navigation.feature
- scripts/gherkin_refs_baseline.json (shrunk)

## Test Evidence

Targeted vitest on the calendar folders; gate run in the PR body. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
