# AE-0473 — Sidebar: fake Chat badge, unreachable Palettes/Knowledge/Analytics/Users

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-14 + SITE-15
Branch: fix/ae-0473-dashboard-sidebar
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The dashboard sidebar reaches every dashboard page (Users for admins only) and shows no invented counts.

## Problem

Found by the AE-0453 site scan. SITE-14: the sidebar's Chat item carried a hard-coded badge "3" on every page.
SITE-15: Palettes, Knowledge, Analytics and `/admin/users` were reachable only by URL; the old `Header` and
`MobileNav` listed them but nothing rendered those components.

## Scope (owner decision, 2026-10-22)

- Remove the Chat badge (no badge until a real unread count exists).
- Add Palettes, Knowledge, Analytics (Management) and an Admin section with Users; items may be `access: "admin"`
  and the sidebar shows them only to admins (`visibleSidebarSections`).
- pt/en labels (`common.sidebar`).
- Delete the dead `components/layout/header.tsx` + `mobile-nav.tsx` (and tests) and the dead-component feature
  `header_public_chat.feature` (its 8 grandfathered scenarios leave the baseline); the live dashboard menu button
  now carries the "mobile menu button label comes from the translations" scenario.

## Non-Goals

- A real unread counter.

## Acceptance Criteria

- [x] Sidebar links `/dashboard/palettes`, `/dashboard/knowledge`, `/dashboard/analytics`.
- [x] `/admin/users` only for admins.
- [x] No badge on Chat; every label in en and pt.

## Repro Steps

1. Open any dashboard page as admin.
2. Before: Chat "3", no Palettes/Knowledge/Analytics/Users. After: all reachable, no badge.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 06:55

Failing tests first (3 red); fix; dead components removed; CI freeze (rule 11): committed locally.

### 2026-10-22 08:30

CI "E2E auth baseline" failed: with the admin items the sidebar was taller than a 720 px viewport and did not
scroll, so Logout was off-screen and unclickable. The link list now scrolls (`overflow-y: auto`, `min-height: 0`);
verified on a local build at 1280×720 (Logout at y≈677, clickable).

## Files Touched

- frontend/src/components/organisms/constants.ts, neon-sidebar.tsx, neon-sidebar-parts.tsx
- frontend/src/schemas/neon-sidebar.ts
- frontend/src/components/organisms/neon-sidebar-items.test.tsx (new)
- frontend/src/app/dashboard/dashboard-menu-button.test.tsx (new)
- frontend/src/components/layout/header.tsx, header.test.tsx, mobile-nav.tsx, mobile-nav.test.tsx (deleted)
- frontend/src/components/layout/index.ts
- frontend/tests/features/header_public_chat.feature (deleted), dashboard-sidebar-ae0473.feature (new)
- scripts/gherkin_refs_baseline.json (8 entries removed, none added)
- frontend/src/i18n/locales/en.json, pt.json

## Test Evidence

Local frontend gates (lint, typecheck, gherkin-refs, format, integrity, dead-code, blog-v1-dead-code, duplication,
dead-files, legacy-guard, legacy-inventory, component-types, schema-drift, test 2026): PASS. Mutation: CI only.

## QA Report

Pending (CI on the PR head).

## Blockers

CI freeze (rule 11) — push pending.
