# AE-0466 — Logged-out unknown URLs redirect to login instead of 404

Status: In Development
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-10
Branch: fix/ae-0466-unknown-url-404
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Unknown URLs answer the not-found page (HTTP 404) for everyone; only real protected pages ask for a login.

## Problem

Found by the AE-0453 site scan (SITE-10). Logged out, `/nonexistent` (any typo or broken external link)
redirected to `/login?redirect=%2Fnonexistent`: visitors met a login wall and crawlers saw 200 for every unknown
URL. The middleware redirected every non-public path when there was no session.

## Scope

- `isGuardedRoute` (identity guards): the login page, `/dashboard*`, `/admin*` and the legacy editor paths.
- The middleware lets every other path through to the router (not-found page, HTTP 404); guarded paths keep the
  existing anonymous / stale-cookie / role handling.

## Non-Goals

- No change to which dashboard/admin pages need which role.

## Acceptance Criteria

- [x] Logged out (or with a stale cookie), `/nonexistent` and `/blog-archive/2024` answer 404 without a redirect.
- [x] `/dashboard/*`, `/admin/*` and the legacy editor paths still redirect to `/login?redirect=…`.

## Repro Steps

1. Logged out, open `https://marinssolutions.com/nonexistent`.
2. Before: redirect to the login page. After: the not-found page, HTTP 404.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 03:20

Failing middleware tests first (4 red), fix; proven on a local `next start` (unknown → 404, protected → 307 login).

## Files Touched

- frontend/src/middleware.ts (+ test)
- frontend/src/modules/identity/guards.ts
- frontend/src/modules/identity/index.ts
- frontend/tests/features/unknown-url-404-ae0466.feature (new)

## Test Evidence

See PR. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
