# AE-0214 — i18n completeness lint (every referenced key exists in every locale)

Status: Dev Complete
Tier: T1
Priority: Low
Type: Quality
Area: frontend
Owner: Unassigned
Branch: feat/kz-content
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

- [x] i18n-completeness lint added and wired into `npm run lint` (as `lint:i18n`).
- [x] The lint FAILS on a seeded referenced-but-missing key (and PASSES on the real config).

## Repro Steps

1. A component uses `useTranslations("create")` + `t("preview.previousSlide")`.
2. The locale JSON carries that string only under `publish.carouselViewer.*`, so `create.preview.previousSlide` is absent.
3. next-intl logs `MISSING_MESSAGE` and renders the raw key on the nav button. No lint caught it.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: full lint gate ([[full-lint-gate-not-bare-eslint]])

## Progress Log

### 2026-06-18

- Ticket created.
- Added `frontend/scripts/check-i18n-completeness.mjs`: binds each `useTranslations`/`getTranslations("ns")` alias to its namespace, resolves static `t("key")` references to `ns.key`, and fails if any key is absent from any locale. Dynamic keys (template literals / variables) are skipped. Allow-list JSON for static exemptions (`i18n-completeness-allowlist.json`, currently empty).
- Wired into `npm run lint` chain as `lint:i18n`.
- Deviation from the ticket Non-Goal: the lint surfaced that the keys are NOT correctly present even on `origin/main` — `create.preview.previousSlide`/`nextSlide` exist only under `publish.carouselViewer.*`, and the entire `admin` namespace (49 keys, `useTranslations("admin")`) was missing from both locales. To satisfy the hard "real config must PASS" requirement, both gaps were filled in `en.json`/`pt.json`. These are real latent i18n bugs the lint was built to prevent, not optional scope.
- Seeded vitest test verifies the real tree passes, a missing key fails, and dynamic/allow-listed/aliased cases behave correctly.

## Files Touched

- `frontend/scripts/check-i18n-completeness.mjs` — the checker (new).
- `frontend/i18n-completeness-allowlist.json` — static-exemption allow-list (new, empty).
- `frontend/package.json` — add `lint:i18n` and wire into `lint`.
- `frontend/src/i18n/locales/en.json`, `pt.json` — add missing `create.preview.previousSlide`/`nextSlide` + full `admin` namespace.
- `frontend/src/scripts/i18n-completeness.test.ts` — seeded test (new).

## Test Evidence

```
npx vitest run src/scripts/i18n-completeness.test.ts
Test Files  1 passed (1)
     Tests  6 passed (6)
```

Real config passes the lint:
```
i18n completeness OK: 434 static key reference(s) across 377 file(s); all present in 2 locale(s) (en, pt).
```

Gate reproduction (`scripts/ci/gates.sh frontend`):
```
GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[...]}
```
All 17 gates PASS (incl. `lint` containing the new `lint:i18n`, `format`, `test`, `dead-code`, `dead-files`, `build`, `integrity`).

Integrity (`scripts/ci/check-integrity.sh frontend`): 0 net-new blockers, 0 warnings.

## QA Report

Pending.

## Blockers

None.
