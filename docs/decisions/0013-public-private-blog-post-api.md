---
status: proposed
date: 2026-07-01
decision-makers: Pedro Marins
consulted: architect-skill, external GLM 5.2 skeptical review
informed: delivery team
---

# ADR-0013: Split Blog-Post Reads into a Public API and a Private/Admin API

## Context and Problem Statement

The public site (homepage "latest posts" and public blog) currently reads **carousel projections**
(`GET /api/carousels?public=true`, `GET /api/carousels/{id}/blog/{lang}`), not the `blog_posts`
table. Every `GET /api/blog-posts*` route is authenticated (`EditorUser`). Consequently a real
`blog_posts` record (e.g. `/blog/e7e871c7-…`) has no public data path and 404s (AE-0297).

We need public visitors to read published posts from the canonical `blog_posts` store, while
administrators need a richer view that includes drafts and editorial internals.

## Decision Drivers

- Public visitors must see published posts by their `blog_posts` id/slug.
- Editorial/AI internals (comments, version history, AI suggestions/metadata, reviewer/author ids)
  must never leak to anonymous users.
- `blog_posts` row remains the single source of truth (ADR-0009, ADR-0011) — no second store.
- Reuse the established carousel public/private auth pattern.

## Considered Options

1. **Two-endpoint split** — a public, unauthenticated, published-only, lean-schema read surface
   plus the existing private `EditorUser` full-detail surface.
2. **Keep public reader carousel-only** — never serve `blog_posts` publicly; fix admin links to
   point at carousel-projection URLs instead.
3. **Single endpoint with optional auth** — one route that widens its payload/filters by role.

## Decision Outcome

Chosen: **Option 1 (two-endpoint split)**.

- **Public** (`GET /api/public/blog-posts`, `GET /api/public/blog-posts/{id_or_slug}`):
  **no auth dependency at all** (mirrors the fully-public carousel media route `media.py:153-178`;
  we deliberately do NOT use `get_optional_user` — the public route resolves no user identity, so
  no code path can ever branch payload/visibility on role). Server-forced `status == published`;
  **all** non-published states ⇒ a **uniform 404** (draft/under_review/approved/archived alike) —
  no 403, no 410. A uniform 404 discloses nothing about existence *or* lifecycle (410-for-archived
  would reveal a resource once existed — rejected for that leak). Returns a **lean allow-list**
  schema built by explicit field mapping (never `from_orm`). Two structural guards (not review
  discipline): (1) a `.feature` asserts an authenticated editor hitting the public route gets the
  **byte-identical** anon payload for a published post and **404** for their own draft; (2) a test
  asserts the public route handler's **dependency tree contains no auth dependency** — so a future
  "harmless" `get_optional_user` addition fails the build, closing the silent-regression path.
- **Private/admin** (existing `GET /api/blog-posts`, `GET /api/blog-posts/{id}`, `EditorUser`):
  full `BlogPostResponse`, all statuses incl. draft, unchanged.

Option 3 rejected: role-branching payloads on one route is the classic over-exposure footgun
(a mapping mistake leaks internals to anon). Option 2 rejected by product: the homepage should be
powered by the canonical blog store.

### Public read model — exact field allow-list (v1)

Built by **explicit field mapping** from the ORM row (never `from_orm`/`model_validate` of the full
model). Public payload = **only**: `id`, `slug`, `title`, `excerpt`, `content` (detail only),
`featured_image_url`, `published_at`, `meta_title`, `meta_description`, `keywords`, `canonical_url`,
`origin`, `project_id` (nullable — enables carousel design enrichment on the FE). All of these are
public-safe (verified: SEO is flat columns, there is no `seo_meta` JSONB blob).

**`project_id` exposure is intentional (external QA F-2, 2026-07-01):** the anonymous payload
deliberately reveals the blog↔carousel correlation for carousel-origin posts, because the public
detail page needs the project id to fetch the (already-public) carousel design tokens via
`GET /carousels/{id}/design`. The correlated resource is gated by its own `is_public` flag, so no
non-public data becomes reachable through the correlation. Removing it would require server-side
design resolution — a deliberate future option, not a v1 requirement.

**Excluded (never serialized publicly):** `status`, `author_id`, `reviewer_id`, `editor_comments`,
`version_history`, `ai_suggestions`, `ai_generation_metadata`, `lock_version`, `distribution`,
`sources`, `citations`. `distribution`/`citations` are **omitted in v1** (not needed to render a
blog page; keeps the anonymous surface minimal). Any later inclusion requires an explicit per-key
sub-allow-list, not a raw JSONB pass-through.

**Security test is recursive:** the regression test serializes the public payload and asserts none
of the excluded key names appear **anywhere in the JSON, including nested objects** — closing the
nested-JSONB leak path.

### No write-on-read

The public GET routes perform **zero writes** to the canonical row. `view_count` is **omitted from
the public schema in v1** (no anonymous view-count increment — it would falsify the read-only
invariant and create an unauthenticated write/contention/scraping vector). If public analytics are
wanted later, they are emitted **out-of-band** (fire-and-forget event to Redis Streams / a separate
counter), never a synchronous write on the read path — a follow-up ticket, not this contract.

### Rate limit (committed contract, not a "consideration")

Both public routes carry a **committed per-IP rate limit**: **MUST be ≤ 120 req/min/IP in v1**
(baseline 60), → **429**. The `.feature` asserts the limit fires at/under the bound (not merely
"some 429 eventually") so the enumeration-cost bound is actually enforceable from the artifact, not
aspirational. With `no-store` + no edge cache every hit is a fresh DB read, so this bounds
**per-IP** enumeration/scraping and id enumeration cost. The upper bound (≤120) is normative; only
the exact value within it is tunable. (Distributed / rotating-IP scraping is out of scope for a
per-IP limit — a WAF/bot-defense follow-up, not an auth-bearing control, since the route is
deliberately identity-free.)

### Single canonical URL (no dual-feed divergence)

There is **one** public URL per post: `/blog/{id}`. Resolution is **by `id` only in v1** — slug
resolution is deferred to a follow-up (with a guard that no slug value may take a UUID shape) to
avoid an id/slug namespace-collision oracle that would defeat the uniform-404 property. The public
detail page **branches on data availability**: `origin == carousel` **and** `project_id` non-null →
carousel design path (design tokens); otherwise → lean `blog_posts` payload with a **default public
theme**. The homepage/blog feed comes from `GET /api/public/blog-posts` (published), each item
linking to that single `/blog/{id}`.

**Parent-carousel deletion is deliberate, not silent:** deleting a carousel project **flips its
orphaned `origin==carousel` blog row to `draft`** (dropping it from the public filter) as part of
that flow — `ON DELETE SET NULL` on `blog_posts.project_id` (`models/blog_post.py:28-32`) alone
would otherwise leave a phantom published row rendering degraded default-theme content the author
never reviewed. So a carousel-origin post never stays public in a degraded shape after its parent
is removed.

### Degraded-mode fallback (no new exposure)

The homepage/blog **list** may fall back to the **existing** public carousel feed
(`GET /api/carousels?public=true`) on public-endpoint error. This is **not** a new leak: the
carousel feed is *already* the current public homepage source and is rendered through its **own
existing validated schema/component**, never merged into (or widened past) the lean blog schema —
so the fallback can surface nothing that isn't already public today. The **detail** page is
fail-closed (explicit "temporarily unavailable"), never a silent shape switch.

### Caching contract

v1 public routes set `Cache-Control: no-store` (pinned, not "short max-age"), and the Next.js
server-side fetch uses `cache: "no-store"`. A `.feature` asserts the exact header on **both** the
list and detail responses. Rationale: `unpublish`/hide flips status→`draft`, so any cached 200
would keep hidden content public until TTL; `no-store` makes hide take effect immediately.
Introducing any CDN/edge cache later is a **behavior change requiring an ADR amendment + a tested
purge path** (unpublish must purge the public cache for the affected `id`/`slug`) — it is not a
silent config flip.

### Server-side fetch is anonymous (verified)

The public homepage/detail are rendered server-side via `lib/server-fetch.ts` `validatedFetch`,
which builds `fetchOptions` with **only** `cache`/`next.revalidate` — **no `headers`, no
`credentials`, no cookie forwarding** (verified). So the server-side call exercises the public
route as a true anonymous client; an editor's session never leaks into it. Prod reachability uses
the `API_BASE_URL` server-side override (or `PRODUCTION_BACKEND_URL` fallback) in `getBaseUrl()`.
A `.feature`/integration test asserts the server-side internal fetch sends no cookie/Authorization
header and returns the byte-identical anon payload.

### Consequences

- Good: clear trust boundary; minimal lean payload (allow-list, recursively tested); single source
  of truth preserved (strictly read-only projection, no view-count write); one canonical URL;
  reuses `assert_*_public` pattern.
- Bad/again: public content contract changes → this ADR; the public detail page must render posts
  that lack carousel design tokens (default public theme); a caching+purge follow-up is owed.

### Confirmation

Backend `.feature` tests assert: public list = published only (client status filters ignored);
public detail 404s for every non-published status; lean payload contains **none** of the excluded
keys **recursively** (explicit security assertion); public GET performs no DB write; private routes
still return drafts to author/admin.

## More Information

Related: ADR-0009 (modular monolith), ADR-0011 (canonical distribution home). Tickets: AE-0297
(this), AE-0295 (admin listing crash), AE-0296 (hide/unpublish gates public visibility).
