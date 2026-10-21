# AE-0444 — Public Visual Carousels page (/carousels list + /carousels/[id] viewer)

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Frontend
Owner: Claude (worker agent, owner-requested)
Agent Lane: developer → qa → release
Branch: feat/ae-0444-public-carousels-page
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

A visitor can browse every published carousel at `/carousels` and open a
responsive, accessible, SEO-indexable slide viewer at `/carousels/[id]` without
an account. The page shows only `is_public` + `COMPLETED` projects; everything
else is a uniform 404.

## Problem

The public site exposes blog posts and chat, but the visual carousels (the
project's most distinctive output) have no public gallery or viewer. The only
slide read (`GET /api/carousels/{id}/slides`) is owner/admin-only and returns
internal `image_path` values, so it cannot back a public page. Prod currently
has 15 public + completed carousels with no public surface for them.

## Scope

- `GET /api/carousels/{project_id}/public` — lean, anonymous projection:
  title/subtitle (PT + EN), language, created date, slide count, available
  languages, `slides_by_language` (`pt`/`en` → `{slide_number, heading,
  image_url}`), and `cover_url`. No `image_path`, `output_dir`, owner, or
  preview URLs.
- Access: `is_public` **and** `status == COMPLETED` **and** generated output;
  otherwise a uniform 404 (ADR-0013).
- Additive `language` field to `CarouselProjectResponse` (cards need it).
- Additive `sort=created_at` on the public list so "newest first" is creation
  order; default `updated_at` preserves the existing contract.
- `/carousels` list: server-rendered, 12 per page, newest first, cover (slide 1
  / hero), title, date, content language, slide count, pagination.
- `/carousels/[id]` viewer: prev/next buttons, keyboard arrows, touch swipe,
  dot navigation, `aria-live` counter, PT/EN toggle when both exist, back link,
  prev/next carousel, responsive `next/image`, metadata + OG cover, 404 for
  private/unknown/non-completed.
- Gherkin + unit/integration tests for both surfaces.
- Reuse `toPublicCarouselImageUrl`, `fetchCompletedProjects`,
  `PublicCoverImage`, `NeonCard`/`NeonBadge`/`NeonButton`,
  `MarketingSectionEyebrow`, `ScrollReveal`, neon tokens, and blog text/date
  helpers. Follow impeccable `distill` + `polish`.

## Non-Goals

- No changes to the landing page or the public header nav (AE-0443 owns the
  links).
- No carousel generation, publishing, or owner workflow changes.
- No infinite scroll, likes, comments, or client-side data fetching.
- No change to the existing public `design`/`images` routes.

## Acceptance Criteria

- [x] AC1: `GET /api/carousels/{id}/public` returns only public + completed
  carousels and a lean payload with PT/EN slide image URLs and no internal
  paths; private, unknown, and non-completed IDs all return 404.
- [x] AC2: `/carousels` renders public + completed carousels newest-first with
  cover, title, date, language, slide count, and working pagination; an empty
  feed has a real empty state.
- [x] AC3: `/carousels/[id]` renders slides with prev/next buttons, keyboard
  arrows, touch swipe, dots, `aria-live` counter, and back-to-list link.
- [x] AC4: PT/EN toggle appears only when both languages have slides and swaps
  the rendered slide images; the selected language survives reload via `?lang=`.
- [x] AC5: prev/next carousel links move between public carousels in feed order.
- [x] AC6: metadata/OG use the carousel title + absolute cover URL; unknown or
  private IDs call `notFound()`.
- [x] AC7: responsive + accessible (`next/image`, alt text, focusable carousel
  region, `prefers-reduced-motion` respected).
- [x] AC8: Gherkin + backend unit/integration + frontend Vitest tests; route
  snapshot, OpenAPI artifact, and URL inventory snapshot regenerated.

## Gherkin Scenarios

- `backend/tests/features/public_carousel_view_ae0444.feature`
- `frontend/tests/features/public_carousels_page_ae0444.feature`
- `frontend/tests/features/public_carousel_viewer_ae0444.feature`

## Delta

### ADDED

- Backend public carousel projection endpoint + schemas.
- `assert_carousel_public_completed`.
- `sort=created_at` on the public carousel list.
- `/carousels` and `/carousels/[id]` public routes and viewer components.
- Public carousel fetch helpers + Zod schemas + i18n keys.

### MODIFIED

- `CarouselProjectResponse` gains `language`.
- `_ProjectQuery` / repository ordering support.

### REMOVED

- None.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: no migration (read-only projection)
- API: additive endpoint + two additive fields/params
- Tests: backend + frontend
- Docs: OpenAPI artifact
- Prompts/LLM: none
- Observability: none
- Deployment: no config change

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0412 (public image route), AE-0422/ADR-0013 (public/private
  reads), AE-0443 (header links).

## Implementation Plan

1. Backend: add `language` + `sort`, public projection route/schemas, access
   helper, tests; regenerate route snapshot + OpenAPI.
2. Frontend: schemas/fetchers/constants, list page + cards, viewer + controls,
   metadata/404, i18n, tests; regenerate URL inventory.
3. Gates + QA + Playwright screenshots; PR.

## Decision Log

- **D1 — one lean public endpoint instead of reusing `/slides`.** The auth-only
  slides response exposes `image_path` and one language's rows; making it public
  would leak internals and still need image URL construction. A dedicated
  projection keeps the public contract explicit and testable.
- **D2 — server-side pagination (12/page), not infinite scroll.** Deep-linkable
  pages, crawlable links, keyboard/screen-reader stability, and no client data
  fetching. The feed is small today; pagination still scales.
- **D3 — `sort=created_at` additive parameter.** "Newest first" means creation
  date. Default `updated_at` keeps every existing caller unchanged.
- **D4 — add `language` to the project response.** Additive, non-sensitive, and
  needed to label each card without an N+1 request.
- **D5 — `?lang=` for the viewer toggle.** Mirrors the blog language switch,
  survives reload/sharing, and resets the slide index on switch.
- **D6 — do not edit landing/header.** AE-0443 owns the nav links; this ticket
  only adds the routes.
- **D7 — viewer is image-first.** Rendered slides already contain the copy, so
  the viewer shows images with heading-derived alt text and a counter; it does
  not re-render slide body HTML.

## QA Checklist

- [x] Security reviewed (public projection only, no internal paths, uniform 404)
- [x] Code quality reviewed (ruff/mypy/eslint/tsc)
- [x] Acceptance criteria validated
- [x] Edge cases tested (private, unknown, non-completed, missing images, one
  language, empty feed, first/last slide, pagination bounds)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-20

Ticket authored from the owner brief (no prior ticket file existed). Prod
read-only check confirmed 15 public + completed carousels and the available
design-token image fields. Backend endpoint + frontend pages implemented.

## Files Touched

Pending (filled by the PR).

## Test Evidence

Pending (gate capture pasted in the PR body).

## QA Report

Pending.

## Blockers

None.

## Final Summary

Pending.
