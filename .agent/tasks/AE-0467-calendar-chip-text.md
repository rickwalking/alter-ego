# AE-0467 — Calendar chips show raw HTML and blank, unnamed chips

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-12
Branch: fix/ae-0467-calendar-chip-text
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Every content-calendar chip shows readable text and has an accessible name.

## Problem

Found by the AE-0453 site scan (SITE-12). The Oct 15 chip read
`Por que todo mundo usa <strong>ChatGPT</strong> e não o Claude?` (the stored title carries emphasis markup) and
two Oct 21 chips were 4 px blank bars (`role="button"` without a name — axe `aria-command-name`): prod returns
`title: ""` for those two carousels (rejected at the brief, no topic either; the backend already falls back to
the topic).

## Scope

- `mapCalendarItemToEvent` strips emphasis markup (shared `stripEmphasisMarkup`).
- A chip with an empty title shows `workflow.calendar.untitled` ("Untitled" / "Sem título").
- Every chip carries its title as a `title` tooltip (titles are ellipsised).

## Non-Goals

- Week/Day/Sync/Schedule (AE-0454); grid ARIA row structure; translating the rest of the calendar (SITE-13).

## Acceptance Criteria

- [x] No raw `<strong>` / `**` in chip text.
- [x] Empty titles show the localized placeholder; every chip button has a non-empty name.
- [x] The full title is the chip's tooltip.

## Repro Steps

1. Open `/dashboard/calendar` in October 2026.
2. Before: raw `<strong>` on Oct 15, two blank bars on Oct 21. After: clean text, "Untitled" chips.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 03:35

Prod calendar items inspected (read-only GET); failing tests first (3 red), fix.

## Files Touched

- frontend/src/app/dashboard/calendar/calendar-grid.tsx (+ test, new)
- frontend/src/modules/editorial-operations/board/calendar/helpers.ts
- frontend/src/i18n/locales/en.json, pt.json
- frontend/tests/features/calendar-chip-text-ae0467.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
