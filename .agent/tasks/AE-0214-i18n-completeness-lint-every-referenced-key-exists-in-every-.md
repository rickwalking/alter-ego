# AE-0214 — i18n completeness lint (every referenced key exists in every locale)

Status: Intake
Tier: T1
Priority: Low
Type: Quality
Area: frontend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

A missing i18n key can never ship: an i18n-completeness lint fails when a referenced key is absent from any locale.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`create.preview.previousSlide` / `create.preview.nextSlide` were missing in prod (raw keys shown on the preview nav buttons + `MISSING_MESSAGE` console errors). The keys now exist on main (`en.json`/`pt.json:543-544`, added 2026-06-17) — prod is a **stale build** (a redeploy picks them up) — but **no lint prevents recurrence** (`frontend/scripts/` has no i18n checker).

## Scope

- Add `frontend/scripts/check-i18n-completeness.mjs` (every referenced `t('...')` key exists in every locale), wired into the `npm run lint` chain.
- Seeded test: a referenced-but-missing key fails the lint.

## Non-Goals

- Adding the two specific keys (already present on main; prod just needs a redeploy).

## Acceptance Criteria

- [ ] i18n-completeness lint added and wired into `npm run lint`.
- [ ] The lint FAILS on a seeded referenced-but-missing key.

## Repro Steps

1. ...

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: full lint gate ([[full-lint-gate-not-bare-eslint]])

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
