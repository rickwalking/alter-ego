# AE-0625 — Public privacy policy page (/privacidade)

Status: Dev Complete
Tier: T1
Priority: High
Type: Feature
Area: Frontend
Owner: Claude
Branch: feat/public-privacy-page
Created: 2026-11-11
Updated: 2026-11-11

## Goal

marinssolutions.com has a public privacy policy at `/privacidade`, which Meta requires before Instagram ads run.

## Problem

Meta needs a public privacy policy URL for the site's ads app; the site had none.

## Scope

- Server-rendered public page `/privacidade` in the marketing layout, Portuguese copy verbatim from the owner's
  approved text (privacy policy only; no data-deletion section, by the owner's scope change).
- "Privacidade" link in the marketing footer, next to the copyright.
- `PUBLIC_ROUTE_PATHS.PRIVACY`: public in the middleware, listed in the sitemap; URL inventory snapshot updated.

## Non-Goals

- Do not refactor unrelated code
- No email, CNPJ or address: the only contact is the LinkedIn profile already on the site.
- No English translation of the policy (the page renders the Portuguese text for every visitor).

## Acceptance Criteria

- [x] `/privacidade` renders without login, server-side, in the marketing layout.
- [x] The copy matches the approved text, with its four sections.
- [x] The footer links `/privacidade`.
- [x] The sitemap lists `/privacidade`.
- [x] No email, CNPJ or address on the page.

## Repro Steps

1. Open `https://marinssolutions.com/privacidade`.
2. 404 before this change.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-11

Requested by Pedro (Meta ads unblock). Implemented; frontend gates green.

### 2026-11-11 18:30

Live check after deploy: an English visitor saw raw keys (`privacy.title`). `i18n/request.ts` ignored the explicit
`getTranslations({ locale })` and loaded the visitor's locale, whose file has no policy. Hotfix: the request config
honours an explicit supported locale. Verified on a local production build: the policy renders for `locale=en` and
`locale=pt`.

## Files Touched

- `frontend/src/app/(public)/(marketing)/privacidade/page.tsx` (new) and test
- `frontend/src/app/(public)/(marketing)/marketing-footer.tsx` and test (new), `page.tsx`, `marketing-about-bio.tsx`
- `frontend/src/constants/{public-routes,sitemap,social}.ts`, `frontend/src/modules/identity/guards.ts`
- `frontend/src/lib/page-metadata.ts`, `frontend/src/i18n/locales/{pt,en}.json`
- `frontend/src/app/sitemap.test.ts`, `frontend/src/constants/middleware.test.ts`
- `frontend/scripts/url-inventory.snapshot.json`, `frontend/tests/features/public-privacy-page.feature`
- Hotfix: `frontend/src/i18n/request.ts`, `frontend/src/i18n/request.test.ts` (new)

## Test Evidence

- Page, footer, sitemap, middleware and page-title tests: 65 passed. All frontend gates green (mutation: CI).

## QA Report

Pending.

## Blockers

None.
