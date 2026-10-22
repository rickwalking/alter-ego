# AE-0469 — Every page shares the same `<title>`

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-16
Branch: fix/ae-0469-page-titles
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Every page names itself in a localized `<title>` ("<Page> · Pedro Marins").

## Problem

Found by the AE-0453 site scan (SITE-16). `/`, `/blog`, `/login`, every dashboard page and the 404 page all had
`<title>Pedro Marins · Alter Ego</title>` (only the carousel pages differed): tabs, history and bookmarks were
indistinguishable and screen readers announced no page name (WCAG 2.4.2).

## Scope

- `pageTitles` messages (en/pt) and `lib/page-metadata.ts` (`pageMetadata(key)` → title + og:title,
  `MetadataOnlyLayout`).
- Metadata-only server layouts for client pages: dashboard calendar, rubrics, palettes, personas, knowledge,
  workflow, blog-posts, analytics, create; admin users; login; 403.
- `generateMetadata` on the (server) public blog list and the not-found page; the dashboard overview body moved to
  `dashboard-home.tsx` behind a server page that exports its metadata.
- Home keeps the site title; carousel pages keep theirs; chat untouched (AE-0451).

## Non-Goals

- Descriptions/og images per dashboard page (private pages).

## Acceptance Criteria

- [x] Public: Blog / Sign in / Access denied / Page not found titles, localized.
- [x] Dashboard and admin pages: their own titles, localized.
- [x] Follow-up (#211 review, via AE-0481): a page's `openGraph` replaces the root one in Next.js, so
      `pageMetadata` returns og:type "website" too, and `/blog` sets its own description + og:description (en/pt).

## Repro Steps

1. Open `/dashboard/calendar` in PT. Before: "Pedro Marins · Alter Ego". After: "Calendário · Pedro Marins".

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 04:50

Failing tests first; implementation; titles verified on a local `next start` for 11 routes × en/pt.

## Files Touched

- frontend/src/lib/page-metadata.ts (+ test, new)
- frontend/src/app/page-titles.test.ts (new)
- frontend/src/app/dashboard/{calendar,rubrics,palettes,personas,knowledge,workflow,blog-posts,analytics,create}/layout.tsx (new)
- frontend/src/app/(admin)/admin/users/layout.tsx, login/layout.tsx, 403/layout.tsx (new)
- frontend/src/app/dashboard/page.tsx, dashboard-home.tsx (moved body)
- frontend/src/app/(public)/blog/page.tsx, not-found.tsx
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/page-titles-ae0469.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
