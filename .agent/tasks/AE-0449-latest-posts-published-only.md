# AE-0449 — Homepage "Latest Posts" shows draft-post content

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Frontend
Owner: Worker (Claude)
Agent Lane: developer → qa → release
Branch: fix/ae-0449-latest-posts-published-only
Kanban Card: TBD
Created: 2026-10-21
Updated: 2026-10-21

## Goal

The landing "Latest Posts" section lists published blog posts only, from the same source as the public
/blog list, and links each card to its public blog post page.

## Problem

Prod, 2026-10-21: https://marinssolutions.com/ "Latest Posts" listed the five newest public completed
carousels (`/api/carousels?public=true&status=completed`). Three of them (901e51bb, 519c7b57, 5344b6c6) are the
source of blog posts that are hidden drafts with the identical title (1feca95c, ec0c1285, f850a410), so the
homepage showed draft posts' title, subtitle and hero. The public blog API itself returned no posts.

## Scope

- Landing data comes from `fetchPublicBlogPosts` (published-only) built with `buildPublicBlogCards`, the /blog
  list builder: one language per card, the post's own cover, the short niche as category, `/blog/<id>` links.
- Public carousels still feed the stats total and the localized copy of carousel-origin posts.
- Zero published posts (or an unavailable feed) shows the existing empty state.
- Backend regression test: the public list and detail exclude draft, hidden (`hidden_bad_post`) and
  future-scheduled posts.

## Non-Goals

- No change to carousel visibility; /carousels keeps listing public carousels.
- No backend behavior change.

## Acceptance Criteria

- [x] A public carousel whose blog post is a draft never renders in "Latest Posts".
- [x] Only published posts render, each linking to `/blog/<post id>`.
- [x] Cards keep one language (title and subtitle from the same locale) and the post's own cover.
- [x] Empty state with no published posts or when the public feed fails.
- [x] Backend pins that draft, hidden and scheduled posts are absent from `/api/public/blog-posts` and 404 by id.

## Gherkin Scenarios

- `frontend/tests/features/landing-latest-posts-published-only-ae0449.feature`
- `backend/tests/features/public_blog_unreleased_ae0449.feature`
- `frontend/tests/features/landing-card-language-ae0446.feature`: the obsolete scenario "A landing card opens
  the carousel it shows" is removed (the landing no longer lists carousels).

## Affected Areas

- Backend: tests only
- Frontend: `src/app/(public)/(marketing)/`
- Tests: frontend unit, backend integration

## Dependencies

- Related: AE-0446 (landing card language), AE-0297 (public blog API)

## Public-surface audit (read-only, prod, 2026-10-21)

- `/api/public/blog-posts`: empty (no published posts).
- All 26 blog posts (all draft): 404 on `/api/public/blog-posts/<id>`, `/blog/<id>` and `/blog/<slug>`.
- `/api/carousels/<id>/blog` and `/blog/en` for the public carousels: 404.
- `sitemap.xml`: lists no posts (base URL is the `your-domain.com` placeholder; separate finding).
- `/rss.xml`, `/feed`, `/feed.xml`, `/atom.xml`: redirect to login; no feed route exists.
- `/blog/<id>` metadata comes from the published-only view, so a draft has no OG tags.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-21

Reproduced with a failing landing test (a draft post's source carousel rendered), switched the section to the
public blog feed, added frontend and backend regression tests. Local: frontend non-mutation gates green
(tests re-run serially for 8 load-timeout files), backend lint and gherkin-refs green, new backend tests pass.
Mutation: CI only.

## Files Touched

- frontend/src/app/(public)/(marketing)/page.tsx
- frontend/src/app/(public)/(marketing)/marketing-latest-posts-data.ts
- frontend/src/app/(public)/(marketing)/marketing-latest-posts.tsx
- frontend/src/app/(public)/(marketing)/marketing-post-cards.tsx
- frontend/src/app/(public)/(marketing)/marketing-helpers.ts
- frontend/src/app/(public)/(marketing)/types.ts
- backend/tests/integration/test_public_blog_unreleased_ae0449.py
