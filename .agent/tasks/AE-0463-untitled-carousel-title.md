# AE-0463 — Published carousels titled "Untitled carousel"

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-07
Branch: fix/ae-0463-untitled-carousel-title
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A published carousel is never titled "Untitled carousel" when it has a topic.

## Problem

Found by the AE-0453 site scan (SITE-07). Five public carousels created 2026-06-14…26 have `title = null` (topic set,
e.g. "GPT 5.6 saiu"). The list cards already fell back to the topic, but the viewer's projection
(`GET /api/carousels/{id}/public`) carried no topic, so the h1, `<title>`, og:title and twitter:title read
"Untitled carousel" in pt and en.

## Scope

- Backend: `CarouselPublicResponse` carries `topic` (already public in the feed).
- Frontend: `publicCarouselTitle` falls back localized title → other-language title → topic → localized
  "Untitled carousel"; the zod schema gains `topic`; `docs/architecture/openapi.json` regenerated.

## Non-Goals

- No data backfill of the stored titles.

## Acceptance Criteria

- [x] Untitled carousel with a topic: heading, page title and share titles read the topic (pt and en).
- [x] A localized title still wins over the topic.
- [x] Neither title nor topic: the localized "Untitled carousel".

## Repro Steps

1. Open `/carousels/e7e871c7-9f5f-4b70-b226-a2d2adeb06fa`.
2. Before: "Untitled carousel". After: "GPT 5.6 saiu".

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 02:20

Root cause from the public API payloads; failing tests first (backend 1, frontend 2 red), fix.

## Files Touched

- backend/src/rag_backend/api/schemas/carousel.py
- backend/src/rag_backend/api/routes/carousels/public_view.py
- backend/tests/unit/api/test_public_carousel_view_ae0444.py
- backend/tests/features/public_carousel_topic_ae0463.feature (new)
- frontend/src/schemas/carousel.ts
- frontend/src/lib/public-carousels.ts (+ test)
- frontend/src/app/(public)/carousels/[id]/page.test.tsx
- frontend/tests/features/public-carousel-title-fallback-ae0463.feature (new)
- docs/architecture/openapi.json (regenerated)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
