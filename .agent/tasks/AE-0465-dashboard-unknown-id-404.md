# AE-0465 — Dashboard unknown ids answer HTTP 200 (soft-404)

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-22
Branch: fix/ae-0465-dashboard-unknown-id-404
Created: 2026-10-22
Updated: 2026-10-22

## Goal

An unknown or malformed carousel / blog post id in the dashboard answers the not-found page with HTTP 404.

## Problem

Found by the AE-0453 site scan (SITE-22). `/dashboard/create/<unknown>` and
`/dashboard/blog-posts/<unknown>/edit` answered HTTP 200 with a client-rendered "Project not found." /
"Blog post not found." (the latter without any h1). Both pages are client components that only learn about the
missing resource after hydration.

## Scope

- `lib/owner-resource.ts`: `checkOwnerResource` asks the backend server-side with the visitor's session cookie
  (only 404 = missing; auth/5xx/unreachable = unknown, the page keeps its own handling);
  `notFoundUnlessOwnerResource` calls `notFound()` for a malformed (non-UUID) id or a missing resource.
- Server `layout.tsx` for `dashboard/create/[id]` (covers the workspace and `/publish`) and
  `dashboard/blog-posts/[id]` (covers `/edit`).
- The blog editor's remaining client not-found / load-error state renders its message as the page h1.

## Non-Goals

- No change to authentication or to the client pages' own loading and error states.

## Acceptance Criteria

- [x] Unknown id → not-found page, HTTP 404 (workspace, publish, blog editor); malformed id → 404 without a
      backend call.
- [x] Existing id → page renders (200); backend 401/403/5xx/unreachable → page renders its own handling.
- [x] Blog editor not-found / error states have an h1.

## Repro Steps

1. Signed in, open `/dashboard/create/00000000-0000-4000-8000-000000000000`.
2. Before: HTTP 200 "Project not found.". After: HTTP 404 not-found page.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 03:05

Failing tests first; fix; HTTP status proven on a local `next start` with a stub backend (missing → 404 for
workspace, publish and editor; existing → 200; malformed → 404).

## Files Touched

- frontend/src/lib/owner-resource.ts (+ test, new)
- frontend/src/app/dashboard/create/[id]/layout.tsx (+ test, new)
- frontend/src/app/dashboard/blog-posts/[id]/layout.tsx (new)
- frontend/src/app/dashboard/blog-posts/[id]/edit/page.tsx (+ test)
- frontend/tests/features/dashboard-unknown-id-404-ae0465.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
