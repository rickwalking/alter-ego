# AE-0462 — Calendar highlights the server's UTC date as "today"

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-04
Branch: fix/ae-0462-calendar-today-timezone
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The content calendar highlights the viewer's local day and opens on the viewer's local month.

## Problem

Found by the AE-0453 site scan (SITE-04). At 21:30 BRT on 2026-10-21 `/dashboard/calendar` highlighted the 22nd,
in every browser timezone tried (Sao_Paulo, Los_Angeles, UTC, Tokyo). The page is a client component but is
server-rendered in UTC; `buildMonthGrid` called `isToday()` during that render and React keeps server-rendered
inline styles on hydration, so the later client renders (same props) never patched the DOM. Clicking next/previous
month fixed it (proof on prod). The month anchor had the same risk on a month's last evening.

## Scope

- `useClientToday()` reads the local day through `useSyncExternalStore` (server snapshot null, re-read each
  minute so it rolls over at local midnight).
- `useCalendarMonth(today)` keeps the viewed month as an offset from today's month; null until today is known.
- `buildMonthGrid` / `buildEmptyCalendarDays` / `buildCalendarDaysFromApi` take `today` explicitly (null
  highlights nothing); `useCalendarDays(anchor, today)` fetches nothing until the anchor exists
  (`useContentCalendar(start, end, enabled)`).
- The page shows the spinner until the local month is known; no grid is rendered on the server.

## Non-Goals

- Week/Day views, Sync, Schedule Post (AE-0454).

## Acceptance Criteria

- [x] Server HTML contains no grid and no highlighted day.
- [x] In the browser the local day is highlighted (21st at 21:30 BRT on Oct 21).
- [x] Last evening of a month opens on that local month; navigation and Today stay relative to it.
- [x] Today rolls over at local midnight while the page stays open.

## Repro Steps

1. At any time when the UTC date differs from the local date (e.g. after 21:00 BRT), open `/dashboard/calendar`.
2. Before: the next day is highlighted. After: the local day.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 02:00

Mechanism proven on prod (initial highlight 22, after next/prev 21); failing tests first, fix.

## Files Touched

- frontend/src/app/dashboard/calendar/use-client-today.ts (+ test, new)
- frontend/src/app/dashboard/calendar/use-calendar-month.ts (+ test)
- frontend/src/app/dashboard/calendar/use-calendar-days.ts (+ test)
- frontend/src/app/dashboard/calendar/page.tsx (+ page.test.tsx, new)
- frontend/src/modules/editorial-operations/board/calendar/helpers.ts (+ test)
- frontend/src/modules/editorial/workflow/hooks/use-content-calendar.ts
- frontend/tests/features/calendar-today-timezone-ae0462.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

origin/main frontend:lint is red on files outside this change (use-project-sources.ts, use-notifications.ts,
personas/page.tsx) — reported to the orchestrator.
