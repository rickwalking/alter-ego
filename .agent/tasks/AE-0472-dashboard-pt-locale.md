# AE-0472 — PT dashboard shows hard-coded English (overview, analytics, calendar grid)

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-13
Branch: fix/ae-0472-dashboard-i18n
Created: 2026-10-22
Updated: 2026-10-22

## Goal

With the interface in Portuguese the dashboard overview, the analytics breadcrumb and the calendar grid are fully
Portuguese.

## Problem

Found by the AE-0453 site scan (SITE-13). In PT the dashboard showed "overview", the three quick-action cards,
"draft · 26 items · Live", "Drafts · 26 in progress · Today", "Weekly velocity · 0 posts/week · Trend"; analytics
showed the "analytics" breadcrumb; the calendar grid showed English legend, "carousel"/"approved" chips and the
empty-month message.

## Scope

- Overview: breadcrumb, quick actions (`QUICK_ACTIONS` now carries a message key), activity lists (status labels
  reuse `dashboard.blogPosts.status`, counts via ICU placeholders).
- Analytics breadcrumb.
- Calendar: legend, content-type and status chips, empty-month message (`workflow.calendar.*`); the English labels
  were removed from the calendar constants.

## Non-Goals

- Calendar toolbar/header (AE-0454), rubrics and personas pages (AE-0455), sidebar (SITE-14/15), knowledge status
  (SITE-23).

## Acceptance Criteria

- [x] PT overview: no English quick-action, activity or breadcrumb text; Portuguese labels present.
- [x] PT analytics breadcrumb "análises".
- [x] PT calendar legend, chips and empty month.

## Repro Steps

1. Switch to PT, open `/dashboard` and `/dashboard/calendar`.
2. Before: mixed English. After: Portuguese.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

Touches `calendar-grid.tsx` like AE-0467 (#207): trivial rebase for whichever lands second.

## Progress Log

### 2026-10-22 06:30

Failing PT-render tests first; fix; CI freeze (rule 11): committed locally.

## Files Touched

- frontend/src/app/dashboard/page.tsx, constants.tsx, dashboard-analytics.tsx, analytics/page.tsx
- frontend/src/app/dashboard/calendar/calendar-grid.tsx, calendar-legend.tsx
- frontend/src/modules/editorial-operations/board/calendar/constants.ts
- frontend/src/i18n/locales/en.json, pt.json
- frontend/src/app/dashboard/dashboard-pt-locale.test.tsx (new)
- frontend/tests/features/dashboard-pt-locale-ae0472.feature (new)

## Test Evidence

Local frontend gates (lint, typecheck, gherkin-refs, format, integrity, dead-code, blog-v1-dead-code, duplication,
dead-files, legacy-guard, legacy-inventory, component-types, schema-drift, test 2039): PASS. Mutation: CI only.

## QA Report

Pending (CI on the PR head).

## Blockers

CI freeze (rule 11) — push pending.
