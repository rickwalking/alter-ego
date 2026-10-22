# AE-0470 — Public and admin accessibility pass (contrast, names, skip link, labels)

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-18 + SITE-19
Branch: fix/ae-0470-a11y-pass
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The public pages, the dashboard shell and the admin pages pass the axe serious/critical checks found by the scan
(calendar grid structure excluded — calendar follow-up).

## Problem

Found by the AE-0453 site scan. SITE-18: the shared dim text colour (`rgba(255,255,255,0.3)`, ~2.6:1) failed WCAG AA
in the footer, sidebar section labels and dashboard card descriptions; the header logo link and the capability
cards had an `aria-label` that omitted their visible text; the hero h1 was announced "Chat with my" three times
(the glitch effect's `::before`/`::after` copies are part of the accessible name); the latest-post placeholder
"▸ carousel_preview.jpg" was read inside the link name; there was no skip link; the dashboard quick actions jumped
from h2 to h4. SITE-19: the admin create-user fields (and the edit-user role) had labels not tied to their
controls; the admin primary button (3.93:1) and error banners (3.7:1) failed contrast.

## Scope

- `TEXT_DIM` / `--color-text-dim` → `rgba(255,255,255,0.5)` (≥ 4.5:1 on page, card and sidebar backgrounds).
- `PublicHeaderBrand` (extracted): brand text always in the link (sr-only below `sm`), no `aria-label`;
  capability cards named by their content (no `aria-label`).
- Hero: glitch copy `aria-hidden` + `sr-only` text; latest-post placeholder `aria-hidden`.
- `SkipLink` (`common.skipToContent`) first in the public, dashboard, admin and login shells; each `<main>` is
  `id="main-content"` `tabIndex={-1}`.
- Admin dialogs: `useId` label/control pairs (create: email, full name, role, password; edit: role); primary buttons
  `bg-primary-700` / `hover:bg-primary-800`; error banners `text-red-800`.
- Dashboard quick-action titles h4 → h3.

## Non-Goals

- Calendar ARIA grid structure and its h1 (calendar follow-up after AE-0467); translating hard-coded strings
  (SITE-13).

## Acceptance Criteria

- [x] axe (local build): `/`, `/blog`, `/carousels`, `/login`, `/nonexistent`, `/dashboard`, `/dashboard/rubrics`,
      `/admin/users` have no violations (before: contrast, label-content-name-mismatch, heading-order).
- [x] Hero h1 accessible name "Chat with my Alter-Ego" (before: the first line three times).
- [x] Skip link first in each shell; admin fields reachable by label.

## Repro Steps

1. Run axe on `/` and `/dashboard`; Tab once on any shell page.
2. Before: contrast and name violations, no skip link. After: clean, "Skip to content" first.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 05:40

axe run on a local build before/after; failing tests first (13 red against main's files); CI freeze (rule 11):
committed locally, pushed once the queue drains.

## Files Touched

- frontend/src/constants/neon.ts, app/globals.css (dim colour) (+ constants/neon-contrast.test.ts, new)
- frontend/src/constants/a11y.ts, components/atoms/skip-link.tsx (+ test, new), app/shell-skip-link.test.tsx (new)
- frontend/src/components/layout/public-header.tsx, app/dashboard/layout.tsx, app/(admin)/admin/layout.tsx,
  app/login/page.tsx
- frontend/src/app/(public)/(marketing)/marketing-hero.tsx, marketing-features.tsx, marketing-primary-feature.tsx,
  marketing-post-cards.tsx (+ marketing-a11y.test.tsx, new; marketing-features.test.tsx)
- frontend/src/components/admin/create-user-dialog.tsx, edit-user-dialog.tsx, change-password-dialog.tsx,
  delete-user-dialog.tsx, app/(admin)/admin/users/page.tsx (+ admin-dialogs-a11y.test.tsx, new)
- frontend/src/app/dashboard/page.tsx (+ dashboard-headings.test.tsx, new)
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/a11y-pass-ae0470.feature (new)

## Test Evidence

Local frontend gates (lint, typecheck, gherkin-refs, format, integrity, dead-code, blog-v1-dead-code, duplication,
duplication-tests, dead-files, legacy-guard, legacy-inventory, component-types, schema-drift, build, test 2051):
PASS. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

CI freeze (rule 11) — push pending.
