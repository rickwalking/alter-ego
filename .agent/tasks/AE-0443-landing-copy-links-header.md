# AE-0443 — Landing copy, card links, header login and hero badge (owner request)

Status: In Progress
Tier: T1
Priority: P1
Type: Bug
Area: Frontend
Owner: Claude (owner request via orchestrator, 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0443-landing-copy-links-header
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

- [ ] AC1: the carousel stat renders the public+completed total from
  `fetchCompletedProjects` (no hardcoded `50+`, no hardcoded replacement).
- [ ] AC2: "8+ years" stays (true, consistent with the About bio); the `∞`
  topics stat is removed, not replaced by a guessed number.
- [ ] AC3: Blog card → `/blog`, Carousels card → `/carousels`, Chat card →
  `/chat`; the whole card is the link, with a visible keyboard focus ring.
- [ ] AC4: public header has no Login link and has "Carrosséis"/"Carousels"
  next to Blog → `/carousels`.
- [ ] AC5: hero renders no "Alter-Ego v2.0" badge; the `hero.badgeVersion` key
  is gone from both locales.
- [ ] AC6: landing copy reviewed in pt/en (grammar, overclaims, latest-posts
  copy), locales key-synced.
- [ ] AC7: Gherkin + component tests (stats total, card hrefs, no login link,
  no badge, copy parity) and frontend gates green locally (CI mutation is the
  source of truth).

## Decisions

- **Stats source**: `data.total` from the existing `fetchCompletedProjects(5)`
  call. `limit=5` only caps the items for the latest-posts cards; `total` is the
  full public+completed count, so no extra request and no guess. Prod on
  2026-10-20 = 15.
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

## Files Touched

Pending.

## Test Evidence

Pending (frontend gates).

## QA Report

Pending.

## Blockers

None.
