# AE-0623 — Public carousel covers follow the reader's language

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Claude
Branch: fix/public-carousel-cover-follows-locale
Created: 2026-11-10
Updated: 2026-11-10

## Goal

With the site in English, the public carousel gallery and share images show the English slides.

## Problem

The gallery card cover was always `design_tokens.images.hero` (the Portuguese slide 1), whatever the reader's
language, so an English reader saw every carousel in Portuguese. The viewer's share image (`og:image`) also used the
API `cover_url`, the first language's slide 1. The viewer's slides already follow the language.

## Scope

- Gallery and neighbor cards: cover is slide 1 rendered in the reader's language, else the hero, else the first slide.
- Viewer metadata: share image is slide 1 of the shown language, else `cover_url`.

## Non-Goals

- Do not refactor unrelated code
- Backend `cover_url` unchanged.

## Acceptance Criteria

- [x] An English reader sees the English slide 1 as each gallery cover.
- [x] A carousel without an English render keeps its Portuguese cover.
- [x] The viewer's share image is slide 1 of the shown language.

## Repro Steps

1. Switch the site to English and open `/carousels`.
2. Every cover is `.../images/slide_1.jpg?lang=pt`.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-10 18:45

Reproduced on prod with the `locale=en` cookie (24 `?lang=pt` covers on the gallery). Fixed; frontend gates green.

## Files Touched

- `frontend/src/lib/public-carousels.ts`
- `frontend/src/lib/public-carousels.test.ts`
- `frontend/src/app/(public)/carousels/[id]/page.tsx`
- `frontend/src/app/(public)/carousels/[id]/page.test.tsx`
- `frontend/tests/features/public_carousels_page_ae0444.feature`
- `frontend/tests/features/public_carousel_viewer_ae0444.feature`

## Test Evidence

- `public-carousels.test.ts` and the viewer page tests: 43 passed.
- Frontend gates run individually, all green (mutation: CI).

## QA Report

Pending (hotfix fast path).

## Blockers

None.
