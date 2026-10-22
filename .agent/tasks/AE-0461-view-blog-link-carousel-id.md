# AE-0461 — Dashboard "View blog" links use the carousel id and open a 404

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-03
Branch: fix/ae-0461-view-blog-link
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Every "View blog" / "View public post" link in the carousel workspace opens a real public page.

## Problem

Found by the AE-0453 site scan (SITE-03). The workspace preview ("View Blog Post") and the publish page
("View public post") built `ROUTE_PATHS.BLOG_POST(project.id)` from the **carousel** id. The public blog is keyed
by the **blog-post** id, so all 19 completed workspaces linked to `/blog/<carouselId>` → 404 (crawl.csv). The
publish page also showed the link after a **failed** site publish.

## Scope

- Backend: `GET /api/public/blog-posts` accepts an optional `project_id` (UUID) and narrows the published-only
  list to that carousel's post (visibility rules unchanged).
- Frontend: `useCarouselBlogPostHref(projectId)` reads the public list with `project_id` and returns
  `/blog/<postId>` or null.
- Workspace preview: "View Blog Post" links the post; hidden when the carousel has no published post.
- Publish page: after a successful site publish, "View public post" links the blog post, else the public carousel
  (`/carousels/<id>`, which the site publish has just made public); no link after a failed publish.

## Non-Goals

- No change to how carousel-origin blog posts are created or published.

## Acceptance Criteria

- [x] `?project_id=<A>` returns only carousel A's published post; a draft-only carousel returns an empty list;
      a malformed id answers 422; the unfiltered list is unchanged.
- [x] Workspace preview links `/blog/<postId>` or shows no link.
- [x] Publish page links the blog post, else `/carousels/<id>`; nothing after a failure.

## Repro Steps

1. Open `/dashboard/create/<completed carousel id>`, click "View Blog Post".
2. Before: `/blog/<carousel id>` → 404. After: the published post, or no button.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 01:45

Root cause from the crawl (19 dead links) and source; failing tests first (backend 2/4, frontend 4 red), fix.

## Files Touched

- backend/src/rag_backend/api/routes/public_blog_post.py
- backend/src/rag_backend/api/schemas/public_blog_post.py
- backend/tests/integration/test_public_blog_project_filter_ae0461.py (new)
- backend/tests/features/public_blog_project_filter_ae0461.feature (new)
- frontend/src/constants/api.ts
- frontend/src/modules/publishing/blog/hooks/use-carousel-blog-post-href.ts (+ test, new)
- frontend/src/modules/publishing/blog/hooks/types.ts
- frontend/src/modules/publishing/index.ts
- frontend/src/app/dashboard/create/workspace/create-carousel-preview.tsx (+ test)
- frontend/src/app/dashboard/create/[id]/publish/page.tsx, publish-page-sections.tsx, use-publish-page.ts (+ page test)
- frontend/tests/features/view-blog-link-ae0461.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
