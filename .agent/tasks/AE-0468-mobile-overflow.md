# AE-0468 — Mobile homepage scrolls sideways; calendar top bar clipped at 375 px

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-11 + SITE-20
Branch: fix/ae-0468-mobile-overflow
Created: 2026-10-22
Updated: 2026-10-22

## Goal

On 375 and 390 px phones the homepage and the content calendar fit the screen width.

## Problem

Found by the AE-0453 site scan. SITE-11: the homepage was 398 px wide on a 375 px phone (405 on 390), so it
panned sideways. Two causes, measured on a local build: the hero's decorative 400 px glow circle beside the terminal
(absolute, right edge at 401) and the About section's social-links row (`display:flex` without wrap). SITE-20: the
calendar's own top bar (fixed `h-14`, no wrap) clipped "Schedule Post" past the right edge.

## Scope

- Hero section: `overflow-x: clip` (no scroll container, decoration clipped to the section).
- Social links row: `flexWrap: "wrap"`.
- `CalendarHeader`: wraps like `NeonTopBar` (min-h-14, flex-wrap, breadcrumb hidden below `sm`, actions on their
  own full-width row).

## Non-Goals

- Calendar toolbar behaviour (AE-0454); translating the header strings (SITE-13).

## Acceptance Criteria

- [x] `/` and `/dashboard/calendar` have scrollWidth == viewport width at 375 and 390 px.
- [x] "Schedule Post" is fully on screen at 375 px.

## Repro Steps

1. Open `/` on a 375 px phone and scroll down. Before: the page pans sideways. After: it does not.
2. Open `/dashboard/calendar` on a 375 px phone. Before: "Schedule Post" clipped. After: on its own row.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 03:55

Overflow sources measured on a local `next start` (stub backend, Playwright 375/390 mobile); guard tests red on
main, green with the fix; after-fix measurement: scrollWidth == viewport on both pages and widths.

## Files Touched

- frontend/src/app/(public)/(marketing)/marketing-hero.tsx
- frontend/src/app/(public)/(marketing)/marketing-about-bio.tsx
- frontend/src/app/(public)/(marketing)/marketing-mobile-fit.test.tsx (new)
- frontend/src/app/dashboard/calendar/calendar-header.tsx (+ test, new)
- frontend/tests/features/mobile-no-horizontal-scroll-ae0468.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
