# AE-0443 — Landing copy, card links, header login and hero badge (owner request)

Status: Review
Tier: T1
Priority: P1
Type: Bug
Area: Frontend
Owner: Claude (owner request via orchestrator, 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0443-landing-copy-links-header
PR: #164
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

The landing page only makes true, meaningful claims (derived from data, not
hardcoded guesses), every capability card links to its public section, the
public header no longer offers Login but does offer Carousels, and the hero no
longer shows the "Alter-Ego v2.0" badge.

## Problem

Owner review, 2026-10-20:

1. The stats block hardcodes "50+ Carrosséis Publicados". Prod truth is 15
   public + completed carousels (read-only prod SELECT, 2026-10-20:
   `select count(*) from carousel_projects where is_public = true and status =
   'completed'` → **15**). 10 of them were published to Instagram by autopilot.
   The "∞ Tópicos Explorados" stat is not a measurable claim.
2. Landing copy in pt/en contains a Portuguese grammar error
   (`about.paragraph2` "Especializo me em"), promises the assistant "sabe tudo"
   / "knows everything", and the latest-posts subtitle claims blog posts while
   the section only renders carousel projects.
3. "What You Can Explore" cards are plain `<div>`s with no links.
4. The public header shows a Login link; `/login` must stay reachable by URL
   only. There is no Carousels nav item even though AE-0444 adds `/carousels`.
5. The hero renders an "Alter-Ego v2.0" badge that no longer means anything.

## Scope

- `frontend/src/app/(public)/(marketing)/marketing-stats.tsx` (+ `types.ts`,
  `page.tsx`): render the years claim and the **derived** public-carousel total
  from `fetchCompletedProjects(...).total`; drop the third stat.
- `marketing-features.tsx` / `marketing-primary-feature.tsx`: whole-card links
  (Blog → `/blog`, Carousels → `/carousels`, Chat → `/chat`) with an
  accessible name and a visible focus ring.
- `frontend/src/components/layout/public-header.tsx`: remove the Login link; add
  Carousels next to Blog.
- `frontend/src/constants/public-routes.ts` + `modules/identity/guards.ts`:
  register `/carousels` as a public route (the page itself is AE-0444).
- `marketing-hero.tsx`: remove the version badge (keep the hero itself).
- `frontend/src/i18n/locales/{pt,en}.json`: add `common.nav.carousels`, remove
  `home.hero.badgeVersion` and `home.stats.topics`, review/fix landing copy in
  both locales (keep them in sync).
- Tests + Gherkin.

## Non-Goals

- Do not create the `/carousels` page (AE-0444 owns it); only link to it and
  register the route as public.
- Do not change authentication, the login page, or `/login` reachability.
- Do not touch the dashboard `Header` (`components/layout/header.tsx`); this
  ticket is about the public shell header.
- No backend changes.

## Acceptance Criteria

- [x] AC1: the carousel stat renders the public+completed total from
  `fetchCompletedProjects` (no hardcoded `50+`, no hardcoded replacement).
- [x] AC2: "8+ years" stays (true, consistent with the About bio); the `∞`
  topics stat is removed, not replaced by a guessed number.
- [x] AC3: Blog card → `/blog`, Carousels card → `/carousels`, Chat card →
  `/chat`; the whole card is the link, with a visible keyboard focus ring.
- [x] AC4: public header has no Login link and has "Carrosséis"/"Carousels"
  next to Blog → `/carousels`.
- [x] AC5: hero renders no "Alter-Ego v2.0" badge; the `hero.badgeVersion` key
  is gone from both locales.
- [x] AC6: landing copy reviewed in pt/en (grammar, overclaims, latest-posts
  copy), locales key-synced.
- [x] AC7: Gherkin + component tests (stats total, card hrefs, no login link,
  no badge, copy parity) and frontend gates green locally (CI mutation is the
  source of truth).

## Decisions

- **Stats source**: `data.total` from the existing `fetchCompletedProjects(5)`
  call. `limit=5` only caps the items for the latest-posts cards; `total` is the
  full count for the query, so no extra request and no guess.
  **Correction (2026-10-20, during verification):** `fetchCompletedProjects`
  previously queried `?public=true` only, so `total` counted every public
  project (26 on prod), not completed ones. It now also sends
  `status=completed`, matching its name and the ticket's metric. Prod query
  `?public=true&status=completed` = 15; the landing stat therefore renders 15
  and drafts are never counted. This also keeps the latest-posts list limited
  to finished public projects.
- **Which stats survive**: keep "8+ years" (already stated in the About bio and
  true) and the derived carousel count. Drop "∞ topics": it is neither
  measurable nor meaningful, and a replacement number would be invented.
- **Labels**: PT "Carrosséis publicados" / EN "Published Carousels" explicitly
  mean public (site) carousels, matching the derived count.
- **Copy**: fix `Especializo me` → `Sou especializado`; drop the "knows
  everything/sabe tudo" overclaim; make the latest-posts subtitle describe what
  the section renders (carousel projects); standardize "Alter-Ego" spelling.
- **Cards**: the link wraps the entire card; the visible card text supplies the
  accessible name; `focus-visible` ring + offset keeps keyboard use visible.
- **Route**: add `/carousels` to the public-route guard now so the header link
  works the moment AE-0444 lands, without waiting for auth middleware changes.

## Repro Steps

1. Open `/` (pt and en).
2. Stats show the hardcoded "50+" and "∞"; cards are not links; header shows
   Login; hero shows "Alter-Ego v2.0".

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

Coordinates with AE-0444 (`/carousels` page). Link only; no page here.

## Progress Log

### 2026-10-20

Read-only prod check confirmed 15 public+completed carousels. Ticket created;
specs/tests/code next.

Implemented stats/copy/cards/header/hero changes, Gherkin + component tests.
During local verification the landing rendered 26: `fetchCompletedProjects`
sent only `?public=true`, so `total` counted every public project. Added
`status=completed` (matching the function name and this ticket's metric);
prod now returns 15 and the landing stat matches. Verified on the local dev
server against the public prod read endpoint (no writes), then captured
desktop/mobile screenshots.

## Files Touched

- `frontend/src/app/(public)/(marketing)/{page,marketing-stats,marketing-features,marketing-primary-feature,marketing-hero,types}.tsx` (+ tests)
- `frontend/src/components/layout/public-header.tsx` (+ test)
- `frontend/src/constants/{public-routes,middleware.test,server-fetch}.ts`
- `frontend/src/modules/identity/guards.ts`
- `frontend/src/lib/server-fetch.ts` (+ test)
- `frontend/src/i18n/locales/{pt,en}.json`
- `frontend/tests/features/landing-copy-links-header-ae0443.feature`
- `frontend/package-lock.json` (vite 7.3.5 → 7.3.7 patch for the high-severity audit gate; not gate loosening)
- `docs/pr-assets/ae-0443/landing-{desktop,mobile}.png` (PR evidence)

## Test Evidence

Local frontend gates (all non-mutation, run individually via
`bash scripts/ci/gates.sh frontend:<gate>`; mutation is CI-only):

`lint`, `lint-changed`, `component-types`, `duplication`, `dead-code`,
`blog-v1-dead-code`, `typecheck`, `build`, `legacy-guard`,
`legacy-inventory`, `format`, `security`, `integrity`, `test`,
`schema-drift`, `duplication-tests`, `dead-files` — **all PASS**.

`frontend:test`: 207 files / 1706 tests passed. New coverage:
`marketing-stats.test.tsx` (15, no 50+/∞), `marketing-features.test.tsx`
(card hrefs/focus), `public-header.test.tsx` (no Login, Carousels),
`landing-copy.test.ts` (pt/en parity + copy fixes),
`server-fetch.test.ts` (`status=completed` filter).

Screenshots: `docs/pr-assets/ae-0443/landing-desktop.png` and
`landing-mobile.png` (local dev server, public prod read API, 15 carousels).

## QA Report

Pending CI + orchestrator verification.

## Blockers

None.
