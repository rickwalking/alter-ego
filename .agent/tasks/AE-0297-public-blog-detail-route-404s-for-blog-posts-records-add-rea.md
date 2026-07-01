# AE-0297 — public blog detail route 404s for blog_posts records: add real data path

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: fullstack
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

A public blog URL for a real `blog_posts` record (e.g.
`/blog/e7e871c7-9f5f-4b70-b226-a2d2adeb06fa`) renders the post instead of 404ing.

## Problem

The public route and the admin listing read **two entirely different backends**:

- The admin "Blog Posts" listing reads the `blog_posts` table via `GET /api/blog-posts`.
- The public route `frontend/src/app/(public)/blog/[id]/page.tsx` does **not** touch
  `/api/blog-posts` at all. It calls `fetchBlogWithDesign(id, lang)`
  (`frontend/src/lib/server-fetch.ts:73-98`), which reads **carousel projections**:
  `GET /api/carousels/{id}/blog/{lang}` and `GET /api/carousels/{id}/design`
  (`frontend/src/constants/api.ts:39-42`; backend `carousels/media.py:181-259`).

`page.tsx:44-48` calls `notFound()` whenever the fetch returns `null`, and `validatedFetch`
returns `null` on any of: carousel not public (404, `carousel_access.py:21-23`), blog not
generated in that language (404, `media.py:203-210`, defaults to `pt`), `design_tokens` is
`None` (404 `ERR_DESIGN_NOT_GENERATED`, `media.py:238-239`), or Zod parse failure.

Consequence: a URL whose id is a `blog_posts` record — or a carousel that isn't public / lacks a
generated blog projection + design tokens in the requested language — 404s. The example
production URL is a `blog_posts` UUID with no carousel-projection data path, so it always fails.

Secondary prod-only risk: `server-fetch.ts:15-25` `getBaseUrl()` hardcodes
`PRODUCTION_BACKEND_URL = "http://backend:8000"` (`constants/api.ts:165`) server-side when
`NEXT_PUBLIC_API_URL` starts with `/`; if that internal Docker hostname is unreachable in prod,
every public fetch throws → `notFound()` for all posts. Rule out before shipping.

## Decision (made — 2026-07-01, user directive)

**Two-endpoint split (Option A, formalized).** Add a dedicated **public**, unauthenticated,
published-only, **lean-schema** blog-post read surface (serves the homepage + public blog), and
keep the existing **private/admin** (`EditorUser`) surface returning full detail **including
drafts**. Recorded in **ADR-0013** (`docs/decisions/0013-public-private-blog-post-api.md`, proposed).
Full plan: `.agent/reports/AE-0297.arch-plan.md`.

- Public: `GET /api/public/blog-posts` (list) + `GET /api/public/blog-posts/{id_or_slug}` — forced
  `status == published`; non-published ⇒ **404** (no existence leak); lean **allow-list** schema
  built by explicit field mapping (never `from_orm`), stripping editor/AI/author internals.
- Private/admin: existing `GET /blog-posts` + `GET /blog-posts/{id}` (`EditorUser`), full
  `BlogPostResponse`, all statuses incl. draft — the "more capabilities" surface.
- Public detail renders `blog_posts` content with a **default public theme** when the post lacks
  carousel design tokens (do not 404 for missing tokens); carousel-derived posts may enrich via
  `/design` additively.
- Hide/unpublish (AE-0296) flips status out of `published`, so the public filter naturally drops
  it. Coordinate with AE-0295 (status badge) and AE-0296.

## Scope

- Determine (architect) whether `/blog/[id]` should serve `blog_posts` records or remain
  carousel-projection-only, and document the decision.
- Implement the chosen option so the example URL (and any published, non-hidden post) renders.
- Rule out / fix the internal `http://backend:8000` base-URL failure mode in prod.

## Non-Goals

- Do not merge the two content systems (carousel projections vs `blog_posts`) into one store.
- Admin listing badge crash (AE-0295) and management controls (AE-0296) are separate.
- No redesign of the public blog reader layout.

## Acceptance Criteria

- [ ] Public list `GET /api/public/blog-posts` returns **only** `published` posts (ignores/rejects
      client status filters), unauthenticated, ordered by `published_at DESC`.
- [ ] Public detail `GET /api/public/blog-posts/{id_or_slug}` returns a published post and **404s**
      for `draft/under_review/approved/archived`/unknown — no existence leak (never 403).
- [ ] The lean public schema contains **none** of: `editor_comments`, `version_history`,
      `ai_suggestions`, `ai_generation_metadata`, `reviewer_id`, `author_id`, `lock_version`
      (asserted explicitly as a security regression test; schema built by explicit field mapping,
      not `from_orm`).
- [ ] Private/admin `GET /blog-posts` + `/blog-posts/{id}` still return full detail incl. drafts to
      author/admin (unchanged).
- [ ] The example production URL for a published post renders its content (default theme when no
      carousel design tokens) instead of 404ing.
- [ ] A hidden/unpublished post (per AE-0296) is **not** publicly viewable (404).
- [ ] The `getBaseUrl()` / internal `backend:8000` prod path is verified reachable, or fixed, so
      public fetches don't uniformly 404.
- [ ] ADR-0013 recorded (proposed) for the public content-contract change.

## Gherkin Scenarios

```gherkin
Feature: Public blog detail resolves real posts

  Scenario: Published post renders publicly
    Given a published, non-hidden blog post with id X
    When an anonymous visitor opens /blog/X
    Then the post content is rendered
    And the response is not a 404

  Scenario: Hidden post is not publicly viewable
    Given a blog post that has been hidden/unpublished
    When an anonymous visitor opens /blog/{that id}
    Then the page returns not-found

  Scenario: Unknown id returns not-found
    Given an id that matches no post or projection
    When an anonymous visitor opens /blog/{id}
    Then the page returns not-found
```

## Repro Steps

1. In production open `https://marinssolutions.com/blog/e7e871c7-9f5f-4b70-b226-a2d2adeb06fa`
   (a real `blog_posts` UUID).
2. Observe 404 / not-found, despite the post existing in the DB and appearing via `/api/blog-posts`.

## Affected Areas

- [ ] Backend (only if Option A: new public `GET /api/blog-posts/{id}` projection + visibility gate)
- [x] Frontend
- [x] Tests
- [ ] Docs (ADR if public contract changes)

Files:
- `frontend/src/app/(public)/blog/[id]/page.tsx`
- `frontend/src/lib/server-fetch.ts`
- `frontend/src/constants/api.ts`
- (Option A) `backend/src/rag_backend/api/routes/blog_post.py`

## Dependencies

- Related: AE-0295, AE-0296 (hide/unpublish must gate public visibility).
- Blocked by: architect decision (this ticket's Decision Required section).

## Progress Log

### 2026-07-01

Ticket created from production troubleshooting session. Root cause: public reader is
carousel-projection-only and has no path to `blog_posts` records. Needs architect decision
(A vs B) before development.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

### 2026-07-01 — architect + user

- Resolved the public-contract question: **two-endpoint split** (public lean/published-only +
  private full/drafts). See ADR-0013 and `.agent/reports/AE-0297.arch-plan.md`.
- Lean public schema is an **allow-list** (explicit field mapping) — primary security control
  against future field-leak.
- Public detail uses a **default theme** for non-carousel posts (no 404 on missing design tokens).

### 2026-07-01 — external skeptical review (GLM 5.2, 5 rounds)

Blind cold-critic via `opencode-go/glm-5.2`. Converged R1 WARN(3 BLOCKER) → … → **R4/R5
PROCEED_WITH_CAUTION, "No blockers remain"**; design affirmed sound. Full evidence:
`.agent/reports/AE-0295-0299.skeptical-review.md`. Hardened decisions folded into the plan:
- **No write-on-read** (dropped `view_count`); public GET is strictly read-only.
- **No `get_optional_user`** — route is identity-free; guarded by a **dependency-tree test** (no
  auth dep) + a byte-identical-anon-payload `.feature`, not just payload equality.
- **Uniform 404** for every non-published state (dropped 410-for-archived — it leaked existence).
- **Recursive** excluded-key leak test (nested JSONB safe; verified no `seo_meta` blob;
  `distribution`/`citations` omitted in v1).
- **Committed rate-limit** ≤120/min/IP (per-IP; distributed scraping = WAF follow-up) +
  `Cache-Control: no-store` pinned, both `.feature`-asserted.
- **id-only resolution** in v1 (slug deferred — precondition: verify zero UUID-shaped slugs in prod).
- Fallback: list fail-open (carousel feed, already-public, leak-tested) / detail fail-closed.
- **Deploy order:** carousel-delete→flip-orphan-to-draft lands before/atomically with AE-0296's 409.

## Blockers

None — decision made. ADR-0013 pending acceptance (proposed).
